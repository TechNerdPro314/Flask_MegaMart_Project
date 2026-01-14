import ssl
from app import create_app
 
app = create_app('development')

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain('cert.pem', 'key.pem')
    app.run(debug=True, host='127.0.0.1', port=5000, ssl_context=context)