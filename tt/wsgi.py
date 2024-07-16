from c3papplication import create_c3p_app

app = create_c3p_app()

if __name__ == '__main__':
    app.run(debug=False, threaded = True, port = 8000, host="0.0.0.0")
