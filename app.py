@app.route('/')
def homepage():
    errands = Errand.query.filter_by(status='Pending').all()
    return render_template('homepage.html', errands=errands)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        is_runner = form.is_runner.data.lower() == 'yes'
        user = User(username=form.username.data, password=form.password.data, is_runner=is_runner, is_approved=not is_runner)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            if user.is_runner and not user.is_approved:
                flash('Your account is pending approval.')
                return redirect(url_for('login'))
            login_user(user)
            if not user.is_verified:
                return redirect(url_for('kyc'))
            if user.is_runner:
                return redirect(url_for('runner_dashboard'))
            return redirect(url_for('user_dashboard'))
    return render_template('login.html', form=form)

@app.route('/kyc', methods=['GET', 'POST'])
@login_required
def kyc():
    form = KYCForm()
    if form.validate_on_submit():
        id_document = form.id_document.data
        selfie = form.selfie.data
        id_document_filename = secure_filename(id_document.filename)
        selfie_filename = secure_filename(selfie.filename)
        id_document.save(os.path.join(app.config['UPLOAD_FOLDER'], id_document_filename))
        selfie.save(os.path.join(app.config['UPLOAD_FOLDER'], selfie_filename))
        current_user.id_document = id_document_filename
        current_user.selfie = selfie_filename
        db.session.commit()
        return redirect(url_for('user_dashboard'))
    return render_template('kyc.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.profile_picture.data:
            picture_file = save_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file
        current_user.contact_info = form.contact_info.data
        db.session.commit()
        flash('Your profile has been updated!')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.contact_info.data = current_user.contact_info
    return render_template('profile.html', form=form)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/uploads', picture_fn)
    form_picture.save(picture_path)
    return picture_fn

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if not current_user.is_verified:
        return redirect(url_for('kyc'))
    errands = Errand.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', errands=errands)

@app.route('/create_errand', methods=['GET', 'POST'])
@login_required
def create_errand():
    if not current_user.is_verified:
        return redirect(url_for('kyc'))
    form = ErrandForm()
    if form.validate_on_submit():
        errand = Errand(user_id=current_user.id, description=form.description.data, price=form.price.data, due_date=form.due_date.data, pickup_location=form.pickup_location.data, delivery_location=form.delivery_location.data)
        db.session.add(errand)
        db.session.commit()
        return redirect(url_for('user_dashboard'))
    return render_template('create_errand.html', form=form)

@app.route('/errands/<int:errand_id>', methods=['GET', 'POST'])
@login_required
def errand_details(errand_id):
    errand = Errand.query.get_or_404(errand_id)
    if request.method == 'POST' and current_user.is_runner:
        errand.status = request.form.get('status')
        if errand.status == 'Completed':
            errand.runner_id = current_user.id
            process_payment(errand)
        db.session.commit()
        return redirect(url_for('runner_dashboard'))
    return render_template('errands.html', errand=errand)

@app.route('/runner_dashboard')
@login_required
def runner_dashboard():
    if not current_user.is_runner:
        return redirect(url_for('user_dashboard'))
    if not current_user.is_verified:
        return redirect(url_for('kyc'))
    errands = Errand.query.filter_by(status='Pending').all()
    return render_template('runner_dashboard.html', errands=errands)

@app.route('/accept_errand/<int:errand_id>')
@login_required
def accept_errand(errand_id):
    if not current_user.is_runner:
        return redirect(url_for('user_dashboard'))
    if not current_user.is_verified:
        return redirect(url_for('kyc'))
    errand = Errand.query.get_or_404(errand_id)
    errand.status = 'In Progress'
    errand.runner_id = current_user.id
    db.session.commit()
    return redirect(url_for('runner_dashboard'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    pending_runners = User.query.filter_by(is_runner=True, is_approved=False).all()
    return render_template('admin_dashboard.html', pending_runners=pending_runners)

@app.route('/approve_runner/<int:user_id>')
@login_required
def approve_runner(user_id):
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def process_payment(errand):
    headers = {
        'Authorization': f'Basic {app.config["COINS_PH_API_KEY"]}:{app.config["COINS_PH_API_SECRET"]}',
        'Content-Type': 'application/json',
    }
    data = {
        'amount': int(errand.price * 100),  # Amount in centavos
        'currency': 'PHP',
        'description': f'Payment for errand ID {errand.id}',
        'success_redirect': url_for('user_dashboard', _external=True),
        'fail_redirect': url_for('errand_details', errand_id=errand.id, _external=True),
        'source': {
            'type': 'gcash',  # Example payment method
        }
    }
    response = requests.post(f'{app.config["COINS_PH_BASE_URL"]}/payments', headers=headers, json=data)
    if response.status_code == 201:
        payment_data = response.json()
        transfer_payment_to_runner(errand, payment_data)
    else:
        flash('Payment processing failed.')

def transfer_payment_to_runner(errand, payment_data):
    total_amount = errand.price
    mandar_fee = total_amount * 0.10
    runner_amount = total_amount - mandar_fee
    # Implement logic to transfer the payment amount to the runner
    # This can be done via the Coins.ph API or other means

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    form = MessageForm()
    if form.validate_on_submit():
        recipient = User.query.filter_by(username=form.recipient.data).first()
        if recipient:
            msg = Message(sender_id=current_user.id, recipient_id=recipient.id, message=form.message.data)
            db.session.add(msg)
            db.session.commit()
            flash('Your message has been sent!')
            return redirect(url_for('send_message'))
        else:
            flash('Recipient not found.')
    return render_template('send_message.html', form=form)

@app.route('/messages')
@login_required
def messages():
    received_msgs = Message.query.filter_by(recipient_id=current_user.id).all()
    return render_template('messages.html', messages=received_msgs)

@app.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/errand_history')
@login_required
def errand_history():
    errands = Errand.query.filter_by(user_id=current_user.id).all()
    return render_template('errand_history.html', errands=errands)

if __name__ == '__main__':
    app.run(debug=True)
