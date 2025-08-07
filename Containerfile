# Build stage
FROM registry.access.redhat.com/ubi9/ubi-minimal AS builder

# Set up a working directory
WORKDIR /app

RUN microdnf install -y --setopt=install_weak_deps=0 --setopt=tsflags=nodocs \
    python312 python3.12-pip && \
    microdnf clean all

# Copy the project configuration and required files
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/

# Temporarily switch to root for installation
USER root

# Install the package and its dependencies
# RUN pip install --no-cache-dir .
RUN pip3.12 install -U --no-cache-dir pip uv && \
    uv export --no-hashes > requirements.txt && \
    sed -i '/^-e ./d' requirements.txt && \
    pip3.12 install --no-cache-dir . -c requirements.txt && \
    pip3.12 uninstall -y uv pip

# Runtime stage
FROM registry.access.redhat.com/ubi9/ubi-minimal

RUN microdnf install -y --setopt=install_weak_deps=0 --setopt=tsflags=nodocs \
    python312 && \
    microdnf clean all

# Copy the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/lib64/python3.12/site-packages/ /usr/local/lib64/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Command to run the application
ENTRYPOINT ["python3.12", "-m", "insights_mcp"]
