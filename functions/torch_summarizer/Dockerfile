# Use a consistent build argument for the build directory
ARG BUILD_DIR="/build"

FROM public.ecr.aws/lambda/python:3.11 AS build-image

ARG BUILD_DIR

RUN yum install -y gcc gcc-c++ make cmake zip unzip libcurl-devel && \
    yum clean all && \
    rm -rf /var/cache/yum

RUN mkdir -p ${BUILD_DIR}

COPY requirements.txt .

RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt --target ${BUILD_DIR}

# Clean up unnecessary files to reduce image size
RUN find ${BUILD_DIR} -type d -name "tests" -exec rm -rf {} + && \
    find ${BUILD_DIR} -type d -name "__pycache__" -exec rm -rf {} + && \
    find ${BUILD_DIR} -type f -name "*.pyc" -delete && \
    find ${BUILD_DIR} -type f -name "*.pyo" -delete

FROM public.ecr.aws/lambda/python:3.11

ARG BUILD_DIR

COPY --from=build-image ${BUILD_DIR}/ /var/lang/lib/python3.11/site-packages/

RUN mkdir -p ./pipes/
COPY ./pipes/ ./pipes/
COPY app.py .

# Command can be overwritten by providing a different command in the template directly.
CMD ["app.lambda_handler"]
