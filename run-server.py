#!/usr/bin/env python3
"""
Inicia o servidor da aplicação no backend.
"""

import logging.config

import alembic.config
import uvicorn

import fabriquinha as fabr


logging.config.fileConfig('logging.conf')


if __name__ == '__main__':
    # aplicar migrações
    alembic_args = ['--raiseerr', 'upgrade', 'head']
    alembic.config.main(argv=alembic_args)

    # executar o servidor
    uvicorn.run('fabriquinha.main:app', host='0.0.0.0', port=8000, workers=1)
