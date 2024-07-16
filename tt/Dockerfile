# Dockerfile
FROM github/codeql-cli-bundle:latest

# Set working directory
WORKDIR /codeql

# Copy the source code
COPY . .

# Copy the CodeQL configuration file
COPY codeql-config.yml .

# Run CodeQL analysis
RUN codeql database create codeql-db --language=python --source-root . --overwrite
RUN codeql database analyze codeql-db --format=sarif-latest --output=results.sarif --config-file=codeql-config.yml

