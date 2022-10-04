import json
import os
import string

import boto3
from cerberus import Validator
from email_validator import EmailNotValidError, validate_email


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


def lambda_handler(event, context):
    try:
        # logging
        print(event)

        # input
        input = json.loads(event.get("body", "{}"))

        # check
        validate_inquiry_request(input)

        # logic
        sesClient = boto3.client("ses", region_name=os.environ["REGION"])

        # 本メール(customer -> administrator)送信
        result = send_email(
            sesClient,
            os.environ["SERVICE_ADMIN_MAIL"],
            "%s <%s>" % (input["name"], input["email"]),
            os.environ["SERVICE_ADMIN_MAIL"],
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
                    "name": os.environ["SERVICE_NAME"],
                    "sender_name": input["name"],
                    "source": input["email"],
                    "subject": input["title"],
                    "body": input["message"],
                    "site_url": os.environ["SERVICE_URL"],
                    "mail": os.environ["SERVICE_ADMIN_MAIL"],
                }
            )

        result = send_email(
            sesClient,
            os.environ["SERVICE_ADMIN_MAIL"],
            os.environ["SERVICE_ADMIN_MAIL"],
            input["email"],
            os.environ["REPLY_TITLE"],
            confirm_message,
        )
        if result.get("MessageId") is None:
            raise ("SES Client did not return MessageID. (service -> customer)")

        # out
        # API Gatewayを通すこともありえるので、最初からプロキシ統合のためのLambda関数の出力形式にあわせておく。
        # https://docs.aws.amazon.com/ja_jp/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
        return {"statusCode": 200, "body": result}
    except Exception as e:
        print({"type": type(e), "error": e})
        return {"statusCode": 500, "body": "process is terminated abnormally..."}
