FROM python:3.13-slim

WORKDIR /app

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deno.land/install.sh | sh

ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install bgutil PO token provider for YouTube bot detection bypass
RUN git clone --single-branch --branch 1.3.1 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /app/bgutil-ytdlp-pot-provider \
    && cd /app/bgutil-ytdlp-pot-provider/server \
    && deno install --allow-scripts=npm:canvas --frozen

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY . .

CMD ["bash", "start"]
