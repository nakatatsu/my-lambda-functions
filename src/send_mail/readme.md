# Test Command

## local

        python-lambda-local -f lambda_handler -t 5 main.py send_test_mail.json

## aws

        curl -v -X POST 関数のURL -H "content-type: application/json" -d '{"name": "田中太郎", "email": "test@example.com", "title": "タイトル", "message": "内容内容内容内容内容"}'
