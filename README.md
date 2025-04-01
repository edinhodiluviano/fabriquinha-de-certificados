# Instalação com docker:
Instalar docker compose  
Executar com `docker compose up --build`

# Instalação no Debian 12 (bookworm):
### Postgres
```
sudo apt install postgresql
```

### Python
Instalar [pyenv](https://github.com/pyenv/pyenv):
```
curl -fsSL https://pyenv.run | bash
```

Instalar dependencias para compilar o python ([wiki](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)):
```
sudo apt install \
    build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev \
    curl git libncursesw5-dev xz-utils tk-dev \
    libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

Instalar o python3.13:
```
pyenv update
pyenv install 3.13.2
```

### Traefik
```
wget https://github.com/traefik/traefik/releases/download/v3.3.5/traefik_v3.3.5_linux_amd64.tar.gz
tar -xvzf traefik_v3.3.5_linux_amd64.tar.gz
sudo setcap CAP_NET_BIND_SERVICE=+eip ./traefik
```

### Outras dependencias
Instalar as dependencias do [weasyprint](https://doc.courtbouillon.org/weasyprint/v64.1/first_steps.html):
```
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```


### Ambiente virtual
Criar o ambiente virtual:
```
~/.pyenv/versions/3.13.2/bin/python -m venv .venv
```

Instalar o uv:
```
source .venv/bin/activate
pip install uv
```

Instalar bibliotecas do projeto:
```
source .venv/bin/activate
uv sync --frozen --no-dev
```

# Execução no Debian 12 (bookworm)
### Banco de dados
O processo de instalação normal do postgres via apt ja deve ter inicializado o postgres na máquina.  
Um passo que você deve lembrar de fazer é criar os usuários e senhas do postgres de acordo com o seu arquivo `.env`.

### Proxy Reverso
```
set -a
source .env
nohup ./traefik &
```

### Servidor Web
```
source .env
source .venv/bin/activate
nohup python run-server.py &
```
