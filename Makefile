.PHONY: clean up run_local create_network help

NETWORK_NAME ?= movies_net
CLEAN ?= false

SHELL := /bin/bash

clean:
	@echo "✅ Выполняем очистку..."
	@docker compose -f .docker/docker-compose.yml down
	@echo "✅ Готово!"

create_network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || docker network create $(NETWORK_NAME)

up:
	@if [ "$(CLEAN)" = "true" ]; then \
		$(MAKE) clean; \
	fi
	@$(MAKE) create_network
	@docker compose -f .docker/docker-compose.yml up -d

run_local:
	@python manage.py

help:
	@echo "*********************************************************************"
	@echo "  Управление окружением"
	@echo "*********************************************************************"
	@echo ""
	@echo "  make create_network"
	@echo "      Создаёт внешнюю Docker-сеть $(NETWORK_NAME), если её ещё нет."
	@echo ""
	@echo "  make up [CLEAN=true]"
	@echo "      Поднимает все сервисы (.docker/docker-compose.yml)."
	@echo "      CLEAN=true  — перед запуском выполняет make clean."
	@echo ""
	@echo "  make run_local"
	@echo "      Поднимает приложение локально, без запуска docker-контейнера"
	@echo ""
	@echo "  make clean"
	@echo "      Останавливает и удаляет контейнеры проекта .docker/docker-compose.yml."
	@echo ""
	@echo "  make help"
	@echo "      Показывает эту справку."
	@echo ""
	@echo "*********************************************************************"
