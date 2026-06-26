# Project Context: AI-Powered Restaurant Recommendation System

## Overview

Build an AI-powered restaurant recommendation service inspired by **Zomato**. The system intelligently suggests restaurants based on user preferences by combining structured data with a **Large Language Model (LLM)**.

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Extract relevant fields such as:
  - Restaurant name
  - Location
  - Cuisine
  - Cost
  - Rating
  - (and other applicable fields from the dataset)

### 2. User Input

Collect user preferences:

| Preference | Examples |
|------------|----------|
| Location | Delhi, Bangalore |
| Budget | low, medium, high |
| Cuisine | Italian, Chinese |
| Minimum rating | numeric threshold |
| Additional preferences | family-friendly, quick service |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM reason and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants
- Provide explanations (why each recommendation fits)
- Optionally summarize choices

### 5. Output Display

Present top recommendations in a user-friendly format:

- Restaurant Name
- Cuisine
- Rating
- Estimated Cost
- AI-generated explanation

## Data Source

- **Dataset:** [Hugging Face — ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- **Key fields:** restaurant name, location, cuisine, cost, rating

## Core Components

1. **Data pipeline** — ingest, clean, and query restaurant records
2. **Preference capture** — UI or API for user inputs
3. **Filtering layer** — narrow candidates before LLM processing
4. **LLM integration** — prompt design, ranking, and natural-language explanations
5. **Presentation layer** — formatted recommendation output for the user

## Success Criteria

- Recommendations reflect user-stated location, budget, cuisine, and rating constraints
- LLM output is personalized, readable, and explains *why* each restaurant was chosen
- Results are displayed with name, cuisine, rating, cost, and explanation
