# RepoMetric
GitHub Repository Activity &amp; Collaboration Analyzer

**Live Demo:** [Open RepoMetric](https://repometric-lsgkdcd2tcmhrffrxesyyu.streamlit.app/)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Example Analysis](#example-analysis)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)
- [License](#license)
- [Author](#author)

---

## Overview

GitHub repositories contain valuable information about software development activity, collaboration, issue management, and project progress. However, extracting meaningful insights from this information can require navigating multiple pages and interpreting different types of data.

RepoMetric simplifies this process by collecting repository information through the GitHub API, processing it with Python, and presenting the results through an interactive Streamlit dashboard.

The project focuses on making repository analytics accessible, visual, and easier to interpret.

### Project Objectives

- Analyze public GitHub repository activity.
- Understand contributor participation and collaboration.
- Explore commit history and development trends.
- Examine issues and pull request activity.
- Identify repository health indicators and unusual activity patterns.
- Present findings through interactive charts, tables, and metrics.
- Demonstrate the practical application of Python-based data analytics.

---

## Key Features

### 1. Repository Overview

Get an overview of a public GitHub repository, including available repository metadata and key activity indicators.

### 2. Commit Activity Analysis

Explore commit history and development activity to understand how a repository changes over time.

### 3. Contributor Analysis

Examine contributor participation and compare contributions to understand collaboration patterns.

### 4. Issue Analysis

Explore repository issues and related metrics to understand issue activity and resolution patterns where the available data supports them.

### 5. Pull Request Analysis

Analyze pull request activity and collaboration workflows using available repository information.

### 6. Repository Comparison

Compare multiple repositories to explore differences in development activity, contributors, issues, and other supported metrics.

### 7. Repository Timeline

Visualize repository activity over time to identify periods of increased or decreased development activity.

### 8. Anomaly Detection

Explore unusual patterns in repository activity using the project's implemented anomaly detection functionality. Detected anomalies are analytical signals, not proof of a problem.

### 9. Repository Health Indicators

Review supported repository activity and collaboration indicators to help interpret overall project activity.

### 10. Interactive Visualizations

Explore data through charts, tables, and interactive dashboard elements.

### 11. Search and Filtering

Use available search, filtering, and table controls to focus on relevant records.

### 12. Data Export

Export supported tabular data for further analysis using CSV or Excel-compatible formats where available.

### 13. API Rate-Limit Awareness

The application includes API rate-limit monitoring to help users understand GitHub API usage constraints.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Interactive dashboard and user interface |
| Pandas | Data processing and tabular analysis |
| NumPy | Numerical operations |
| Plotly | Interactive data visualizations |
| GitHub REST API | Retrieval of public repository information |
| Git | Version control |
| GitHub | Source code hosting and collaboration |
| Docker | Containerization support |
| Docker Compose | Container configuration and orchestration |

---

## How It Works

RepoMetric follows a straightforward analytics workflow:

1. **Repository input:** The user provides a public GitHub repository.
2. **Data collection:** The application retrieves supported repository information through the GitHub API.
3. **Data processing:** Python functions organize the retrieved information into analysis-ready structures.
4. **Metric calculation:** The application calculates supported activity and collaboration metrics.
5. **Visualization:** Streamlit and Plotly present the results through interactive dashboard components.
6. **Exploration:** Users inspect, filter, compare, and export available information.

```text
User
  |
  v
Streamlit Dashboard
  |
  v
GitHub REST API
  |
  v
Repository Data
  |
  v
Data Processing
  |
  v
Metrics and Analysis
  |
  v
Interactive Charts and Tables
```

---

## Getting Started

### Prerequisites

Install the following before running RepoMetric locally:

- Python 3.10 or a compatible version supported by the project's dependencies.
- Git.
- A modern web browser.
- Internet access to retrieve GitHub repository data.

### 1. Clone the Repository

```bash
git clone https://github.com/Vinn78/RepoMetric.git
cd RepoMetric
```

### 2. Create a Virtual Environment

**Windows — Git Bash**

```bash
python -m venv .venv
source .venv/Scripts/activate
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

Streamlit will display a local URL, typically:

```text
http://localhost:8501
```

Open the URL in your browser to use the dashboard.

---

## Usage

1. Launch RepoMetric.
2. Enter the URL of a public GitHub repository.
3. Select the analysis or dashboard sections you want to explore.
4. Run the available analysis.
5. Review repository metrics, charts, tables, and insights.
6. Use the available search and filtering controls to investigate specific records.
7. Export supported data when required.

For example, you can analyze a repository such as [pandas-dev/pandas](https://github.com/pandas-dev/pandas) by entering its GitHub URL into the application.

The available results depend on the repository, the API endpoints used by the application, and GitHub API limits.

---

## Project Structure

The primary application files include:

```text
RepoMetric/
├── app.py
├── github_api.py
├── data_processor.py
├── requirements.txt
├── README.md
├── LICENSE
├── Dockerfile
└── docker-compose.yml
```

- **`app.py`** — Streamlit application, dashboard layout, controls, and analysis presentation.
- **`github_api.py`** — GitHub API integration and repository data retrieval.
- **`data_processor.py`** — Data transformation, processing, and analytical calculations.
- **`requirements.txt`** — Python package dependencies.
- **`Dockerfile`** — Instructions for building the application container.
- **`docker-compose.yml`** — Docker Compose configuration.
- **`LICENSE`** — Project licensing terms.

Additional files and directories may be present in the repository.

---

## Example Analysis

RepoMetric can be used to investigate questions such as:

- How active has a repository been recently?
- Which contributors account for the most recorded contributions?
- How does activity change over time?
- What patterns appear in issue and pull request activity?
- How do two repositories differ in their supported metrics?
- Are there unusual changes in activity that deserve further investigation?
- What does the available repository data suggest about collaboration patterns?

These analyses can help students, developers, and project teams explore software development activity using data rather than relying exclusively on manual inspection.

---

## Limitations

- RepoMetric primarily analyzes publicly accessible GitHub repository information.
- Results depend on the availability and completeness of data returned by the GitHub API.
- API rate limits can restrict the frequency or volume of requests.
- Activity metrics are indicators and should be interpreted in context.
- Anomaly detection identifies unusual patterns; it does not establish their cause.
- Repository health indicators are analytical aids and should not be treated as definitive measures of software quality.
- Features and exports depend on the functionality implemented in the current version.

---

## Future Improvements

Potential areas for further development include:

- Expanded repository comparison capabilities.
- More detailed contributor collaboration analysis.
- Additional activity trends and analytical visualizations.
- Improved caching and API request efficiency.
- Historical repository monitoring.
- More configurable date ranges and analysis filters.
- Enhanced dashboard accessibility and user experience.
- Additional testing and deployment automation.

These are potential improvements rather than a claim that they are already implemented.

---

## License

RepoMetric is distributed under the MIT License. See the [`LICENSE`](LICENSE) file for the complete terms.

---

## Author

**Vinayak Goyal**

GitHub: [@Vinn78](https://github.com/Vinn78)

---

## Acknowledgements

- [GitHub REST API](https://docs.github.com/en/rest) for repository data access.
- [Streamlit](https://streamlit.io/) for the interactive application framework.
- [Pandas](https://pandas.pydata.org/) for data analysis and processing.
- [Plotly](https://plotly.com/python/) for interactive visualizations.

---

**RepoMetric — Turning GitHub repository activity into actionable insights.**
