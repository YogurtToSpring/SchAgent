PYTHON   = C:/Users/SumCoincid/miniconda3/envs/newEnv/python.exe

ifeq ($(OS),Windows_NT)
    BG_RUN   = start "$(1)" cmd /c "cd /d $(2) && $(3)"
else
    BG_RUN   = cd $(2) && $(3) &
endif

.PHONY: help install run-backend run-frontend run-langchain run

help:
	@echo "Avaliable Command:"
	@echo "  make install"
	@echo "  make run-backend"
	@echo "  make run-frontend"
	@echo "  make run-langchain"
	@echo "  make run"

install:
	pip install -r Backend/requirements.txt
	pip install -r LangChain-Module/requirements.txt
	cd campusflow-frontend && npm install

run-backend:
	cd Backend && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload

run-frontend:
	cd campusflow-frontend && npm run dev

run-langchain:
	cd LangChain-Module && $(PYTHON) api.py

run:
	$(call BG_RUN,Backend,Backend,$(PYTHON) main.py)
	$(call BG_RUN,Frontend,campusflow-frontend,npm run dev)
	$(call BG_RUN,LangChain,LangChain-Module,$(PYTHON) api.py)
	@echo The services have been started.
