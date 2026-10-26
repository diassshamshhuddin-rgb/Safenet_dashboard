.PHONY: install demo test lint clean

install:
	pip install -r requirements.txt

demo:
	docker compose up --build

test:
	pytest tests/

eval:
	python scripts/evaluate.py

dashboard:
	streamlit run dashboard/app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache