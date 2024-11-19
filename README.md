# AI Team Simulation

An interactive simulation of an AI team using LangChain-powered agents with Flask and Vanilla JS.

## Project Overview

The AI Team Simulation project creates a collaborative environment where specialized AI agents work together to accomplish tasks. Each agent has a unique role and expertise, enabling natural interactions and task delegation within the team.

### Key Features
- Multiple specialized AI agents (PM, Developer, Tester, etc.)
- Real-time chat interface
- Visual representation of agent relationships
- GitHub repository integration
- Inter-agent collaboration and task delegation

## Prerequisites

- Python 3.11 or higher
- Required environment variables:
  - `OPENAI_API_KEY`: OpenAI API key for LangChain
  - `GITHUB_TOKEN`: GitHub personal access token with repository permissions

## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-team-simulation.git
cd ai-team-simulation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Create a `.env` file in the project root
   - Add the following variables:
     ```
     OPENAI_API_KEY=your_openai_api_key
     GITHUB_TOKEN=your_github_token
     ```

## Running the Application

1. Start the Flask server:
```bash
python main.py
```

2. Access the application:
   - Open your web browser
   - Navigate to `http://localhost:5000`

## Features & Usage

### Available AI Agents

- **Project Manager (PM)**: Handles project planning and coordination
- **Business Analyst (BA)**: Analyzes requirements and processes
- **Developer**: Provides technical solutions and implementation
- **Tester**: Ensures quality and performs testing
- **DevOps**: Manages deployment and infrastructure
- **UX Designer**: Designs user interfaces and experiences

### Chat Interface

1. Select an agent from the dropdown menu
2. Type your message in the input field
3. Press Enter or click Send
4. View responses from the selected agent and any collaborating agents

### Agent Relationships View

- Access via the "View Agent Relationships" button
- Interactive visualization showing:
  - Agent connections and relationships
  - Communication paths
  - Role dependencies

### GitHub Integration

1. Access the GitHub integration page
2. Enter repository details
3. Initialize or connect to an existing repository
4. View repository status and information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
