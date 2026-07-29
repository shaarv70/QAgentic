# QAgentic

QAgentic is an AI-powered QA framework designed to analyze software requirements, plan QA artifacts, generate test artifacts, and review generated output using LLMs.

Version: **v0.2.0**

## Features

Requirement analysis
Interactive requirement clarification
Requirement intelligence
QA artifact planning
Functional test case generation
Automation script generation
Requirement summary generation
Database artifact generation
Dependency-aware task execution
Parallel execution of independent tasks
AI-based artifact review
Automatic correction of failed artifacts
Retry mechanism for failed generation
Approved artifact propagation to dependent tasks
Configurable LLM provider architecture
Ollama, Groq, and Gemini integration

## Architecture

The framework follows a layered, extensible architecture using:

Agent architecture
Registry pattern
Provider pattern
Dependency injection
Service layer
Abstract base classes
Execution context
Dependency-aware task planning
Parallel execution using ThreadPoolExecutor
Review and correction workflow

### Execution Flow

User Requirement
→ Requirement Agent
→ Requirement Intelligence Agent
→ Planner Agent
→ Supervisor Agent
→ Execution Agent
→ Tool Registry
→ LLM Service
→ LLM Provider
→ Review Agent
→ Correction if required
→ Approved Artifact
→ Dependent Tasks

Independent tasks can execute in parallel, while dependent tasks execute only after their required artifacts have successfully passed review.

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

Python 3.12+
At least one supported LLM provider

For local execution with Ollama:

Ollama
A locally available Ollama model

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

Create a .env file in the project root.

Example:

GROQ_API_KEY=
GEMINI_API_KEY=
OLLAMA_URL=http://localhost:11434/api/generate
MODEL_NAME=<your-model-name>
LOG_LEVEL=INFO
OUTPUT_FOLDER=output

Configure the variables required for the LLM provider you want to use.

The .env file is excluded from Git and should not be committed.

## Run

Run the application:

python app.py

Enter your QA requirement when prompted.

The framework will analyze the requirement, request clarification when necessary, plan the required QA tasks, resolve dependencies, generate artifacts, review the generated output, correct failed artifacts when applicable, and save approved artifacts.

## Current LLM Support

Ollama
Groq
Gemini

The provider architecture is designed to support additional LLM providers in future versions.

## Status

This is the **v0.2.0** release of the project.

This release extends the initial agent framework with requirement intelligence, dependency-aware task execution, execution context, multiple QA generators, review and correction workflows, approved artifact propagation, and multi-provider LLM support.