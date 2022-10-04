FROM amazon/aws-lambda-python:3.9

RUN yum update -y
RUN yum install -y git go make unzip tar
RUN git clone https://github.com/direnv/direnv && cd direnv && make install && cd ..
RUN echo 'eval "$(direnv hook bash)"' >> /root/.bashrc && source /root/.bashrc
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install
RUN pip install cerberus email_validator boto3 pytest pytest-cov  pytest-mock python-lambda-local


CMD ["/bin/bash"]

