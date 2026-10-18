FROM python:3.11-slim

WORKDIR /app

# Create a non-root user for Hugging Face Spaces security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user:user . .

# Hugging Face Spaces runs on port 7860
ENV PORT=7860
ENV HOST=0.0.0.0
EXPOSE 7860

CMD ["python", "main.py"]
