# Kinship Screening with QAOA: website and reproducible Qiskit environment.
# Python 3.11 matches the version used to produce the committed results/.
#
# Default: serve the project website on port 8000 (for Coolify or any host).
#   docker build -t kinship-qaoa .
#   docker run --rm -p 8000:8000 kinship-qaoa            # then open http://localhost:8000
#
# The same image runs the code:
#   docker run --rm kinship-qaoa python -m kinship.demo   # one-command demo
#   docker run --rm kinship-qaoa pytest                   # 47 checks
#   docker run --rm kinship-qaoa python -m kinship.demo --size M --index 1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user; the demo may write figures to results/.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/', timeout=4)" || exit 1

CMD ["sh", "-c", "python -m http.server ${PORT} --bind 0.0.0.0"]
