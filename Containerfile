# Build stage
FROM registry.access.redhat.com/ubi9/python-312 AS builder

# Set up a working directory
WORKDIR /app

# Copy the project configuration and required files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Temporarily switch to root for installation
USER root

# Install the package and its dependencies
RUN pip install --no-cache-dir .

# Runtime stage
FROM registry.access.redhat.com/ubi9/python-312

# Copy the installed packages from the builder stage
COPY --from=builder /opt/app-root/lib/python3.12/site-packages/ /opt/app-root/lib/python3.12/site-packages/
COPY --from=builder /opt/app-root/bin/ /opt/app-root/bin/

# Command to run the application
ENTRYPOINT ["python", "-m", "insights_mcp"]
