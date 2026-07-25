# QAgentic

QAgentic is an AI-powered QA framework designed to analyze software requirements, plan QA artifacts, generate test artifacts, and review generated output using LLMs.

Version: **v0.1.0**

## Features

- Requirement analysis
- Interactive requirement clarification
- QA artifact planning
- Test case generation
- Parallel artifact execution
- AI-based artifact review
- Retry mechanism for failed generation
- Configurable LLM provider architecture
- Ollama integration

## Architecture

The framework follows a layered, extensible architecture using:

- Agent architecture
- Registry pattern
- Provider pattern
- Dependency injection
- Service layer
- Abstract base classes
- Parallel execution using ThreadPoolExecutor

### Execution Flow

User Requirement  
→ Supervisor Agent  
→ Requirement Agent  
→ Planner Agent  
→ Execution Agent  
→ Tool Registry  
→ LLM Service  
→ LLM Provider  
→ Review Agent

## Project Structure

    agents/         Agent implementations
    artifacts/      Artifact management
    models/         Application state and domain models
    prompts/        LLM prompt builders
    providers/      LLM provider implementations
    registries/     Agent, tool, and provider registries
    services/       Framework services and generators
    utils/          Logging and utility components

    app.py           Application entry point
    config.py        Application configuration

## Requirements

- Python 3.12+
- Ollama
- A locally available Ollama model

## Installation

Clone the repository:

    git clone <repository-url>
    cd AI-QA-Agent

Create a virtual environment:

    python -m venv .venv

Activate it on Windows:

    .venv\Scripts\activate

Install dependencies:

    pip install -r requirements.txt

## Configuration

Create a `.env` file in the project root.

Example:

    OLLAMA_URL=http://localhost:11434/api/generate
    MODEL_NAME=<your-model-name>
    LOG_LEVEL=INFO
    OUTPUT_FOLDER=generated

The `.env` file is excluded from Git and should not be committed.

## Run

Make sure Ollama is running and the configured model is available.

Then run:

    python app.py

Select the application type and enter your requirement.

The framework will analyze the requirement, request clarification when necessary, plan the required QA artifacts, generate them, and review the generated output.

## Current LLM Support

- Ollama

The provider architecture is designed to support additional LLM providers in future versions.

## Status

This is the initial **v0.1.0** release of the project.

The focus of this release is establishing the core agent workflow, registry architecture, LLM integration, artifact generation, and review pipeline.