import json
import os
import string

import boto3
from cerberus import Validator
from email_validator import EmailNotValidError, validate_email

import settings


def is_email(field, value, error) -> None:
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError:
        error(field, "is not mail address.")


def send_email(client, source: str, reply: str, to: str, subject: str, body: str, charset: str = "utf-8") -> dict:

    response = client.send_email(
        Source=source,
        Destination={
            "ToAddresses": [
                to,
            ]
        },
        ReplyToAddresses=[
            reply,
        ],
        Message={
            "Subject": {"Data": subject, "Charset": charset},
            "Body": {"Text": {"Data": body, "Charset": charset}},
        },
    )
    return response


def validate_inquiry_request(request: any) -> None:
    schema = {
        "name": {"type": "string", "required": True, "maxlength": 40},
        "email": {"type": "string", "required": True, "maxlength": 193, "check_with": is_email},
        "title": {"type": "string", "required": True, "maxlength": 80},
        "message": {"type": "string", "required": True, "maxlength": 10000},
    }

    v = Validator(schema)
    v.allow_unknown = True
    if not v.validate(request):
        raise TypeError(v.errors)


def response(statusCode: int, body: string) -> None:
    # https://docs.aws.amazon.com/ja_jp/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
    return {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": os.environ["CORS_ALLOW_ORIGIN"],
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": body,
    }


def get_secrets(secret_name: str, region_name: str) -> string:
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    return get_secret_value_response["SecretString"]


def lambda_handler(event, context):
    try:
        # logging
        print(event)

        # input
        # REST APIかHTTP APIかで入力値の取り方が変わるため、両方に対応させる
        if event.get("body", None) is not None:
            input = json.loads(event.get("body", "{}"))
        else:
            input = {
                "name": event["name"],
                "email": event["email"],
                "title": event["title"],
                "message": event["message"],
            }

        # check
        validate_inquiry_request(input)

        # logic
        admin_mail_address = get_secrets(settings.mail_secret_key, settings.secrets_manager_region)

        # ※ 公開リポジトリにメールアドレスを公開したくなかったのでSecretsManagerを使っているが、
        # Privateリポジトリで使うならこんなことをせずに設定ファイルにメールアドレスを書き込むだけで十分。

        sesClient = boto3.client("ses", region_name=os.environ["REGION"])

        # 本メール(customer -> administrator)送信
        result = send_email(
            sesClient,
            admin_mail_address,
            "%s <%s>" % (input["name"], input["email"]),
            admin_mail_address,
            input["title"],
            input["message"],
        )
        if result.get("MessageId") is None:
            raise ("SES Client did not return MessageID. (customer -> administrator)")

        # 確認用メール(service -> customer)
        with open("confirm_mail_template.txt", "r", encoding="utf-8") as file:
            template = string.Template(file.read())
            confirm_message = template.safe_substitute(
                {
                    "name": settings.service_name,
                    "sender_name": input["name"],
                    "source": input["email"],
                    "subject": input["title"],
                    "body": input["message"],
                    "site_url": settings.service_url,
                    "mail": admin_mail_address,
                }
            )

        result = send_email(
            sesClient,
            admin_mail_address,
            admin_mail_address,
            input["email"],
            settings.mail_reply_title,
            confirm_message,
        )
        if result.get("MessageId") is None:
            raise ("SES Client did not return MessageID. (service -> customer)")

        return response(200, json.dumps("process is successful."))

    except Exception as e:
        print({"type": type(e), "error": e})
        return response(500, json.dumps("process is terminated abnormally..."))
