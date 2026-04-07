FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY smartapi/ smartapi/

RUN pip install --no-cache-dir -e ".[web]"

COPY testcases/ testcases/
COPY environments/ environments/
COPY mock/ mock/

EXPOSE 8100

CMD ["smartapi", "web", "--host", "0.0.0.0", "--port", "8100"]
