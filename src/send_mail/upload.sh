#!/bin/bash

# [USAGE]
# cd /mnt/c/MyFile/GitHub/my-lambda-functions/src/send_mail
# bash ./upload.sh develop

set -eu

if [ -z "$1" ]; then
    echo "環境名を引数で指定してください"
fi
 
ENV=$1
BUCKET_NAME=$ENV-general-tricrow
FILE_NAME=send_mail-$(date +'%Y%m%d%H%M%S').zip
FUNCTION_NAME=$ENV-send-mail
KEY_NAME=backend/lambda/$FILE_NAME

# 要件5. アップロードすべきファイルをZipで圧縮し、S3にPUTする。
zip -j $FILE_NAME ./*.py ./*.txt
aws s3 cp $FILE_NAME s3://$BUCKET_NAME/$KEY_NAME

# 要件6. Lambda関数にアップロードする。関数バージョンも同時に作成する。
aws lambda update-function-code --function-name $FUNCTION_NAME --s3-bucket $BUCKET_NAME --s3-key $KEY_NAME --publish

# 要件7. エイリアスをLATESTに更新する。
aws lambda update-alias --function-name $FUNCTION_NAME --name $FUNCTION_NAME-alias --function-version \$LATEST

rm $FILE_NAME