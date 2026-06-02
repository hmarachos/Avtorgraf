.PHONY: help run dev docker docker-stop clean lint format test backup

help:
	@echo "Avtorgraf - Makefile команды"
	@echo ""
	@echo "  make run          - Запустить приложение локально"
	@echo "  make dev          - Запустить в режиме разработки"
	@echo "  make docker       - Собрать и запустить Docker контейнер"
	@echo "  make docker-stop  - Остановить Docker контейнер"
	@echo "  make clean        - Удалить временные файлы"
	@echo "  make lint         - Проверить код (ruff + mypy)"
	@echo "  make format       - Отформатировать код (black + isort)"
	@echo "  make backup       - Создать резервную копию БД"
	@echo ""

run:
	@echo "🚀 Запуск Avtorgraf..."
	PYTHONPATH=src python -m avtorgraf.main

dev:
	@echo "🔧 Режим разработки (запуск с PYTHONPATH)"
	PYTHONPATH=src python -m avtorgraf.main

docker:
	@echo "🐳 Сборка и запуск Docker контейнера..."
	docker compose up --build -d
	@echo "✅ Приложение доступно на http://localhost:8080"

docker-stop:
	@echo "🛑 Остановка Docker контейнера..."
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	@echo "🧹 Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "✅ Очистка завершена"

lint:
	@echo "🔍 Проверка кода..."
	@command -v ruff >/dev/null 2>&1 || { echo "❌ ruff не установлен. Установите: pip install ruff"; exit 1; }
	@command -v mypy >/dev/null 2>&1 || { echo "❌ mypy не установлен. Установите: pip install mypy"; exit 1; }
	ruff check src/
	mypy src/
	@echo "✅ Проверка завершена"

format:
	@echo "✨ Форматирование кода..."
	@command -v black >/dev/null 2>&1 || { echo "❌ black не установлен. Установите: pip install black"; exit 1; }
	@command -v isort >/dev/null 2>&1 || { echo "❌ isort не установлен. Установите: pip install isort"; exit 1; }
	black src/
	isort src/
	@echo "✅ Форматирование завершено"

backup:
	@echo "💾 Создание резервной копии БД..."
	@mkdir -p backups
	@if [ -f data/avtorgraf.sqlite3 ]; then \
		cp data/avtorgraf.sqlite3 backups/avtorgraf-$$(date +%Y%m%d-%H%M%S).sqlite3; \
		echo "✅ Резервная копия создана в backups/"; \
	else \
		echo "⚠️  Файл БД не найден"; \
	fi

install-dev:
	@echo "📦 Установка инструментов разработки..."
	pip install black isort mypy ruff
	@echo "✅ Инструменты установлены"

health:
	@echo "🏥 Проверка здоровья приложения..."
	@curl -s http://localhost:8080/api/health | python -m json.tool || echo "❌ Приложение недоступно"
