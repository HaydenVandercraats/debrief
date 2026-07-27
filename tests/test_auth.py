def test_index_redirects_to_login_when_logged_out(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_login_with_correct_password_succeeds(client):
    response = client.post('/login', data={'password': 'test-password'}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')


def test_login_with_wrong_password_shows_error(client):
    response = client.post('/login', data={'password': 'wrong'})
    assert response.status_code == 200
    assert b'Incorrect password' in response.data


def test_logout_clears_session(client):
    client.post('/login', data={'password': 'test-password'})
    client.get('/logout')
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
