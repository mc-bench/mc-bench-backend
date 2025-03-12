# MC-Bench Backend Documentation

Welcome to the MC-Bench backend documentation. This documentation provides comprehensive information about the MC-Bench platform for generating, rendering, and comparing Minecraft builds created by different AI models.

## Documentation Sections

### [Architecture Overview](architecture.md)
Detailed description of the system architecture, components, and data flow.

### [Developer Guide](developer-guide.md)
Information for developers working on the MC-Bench backend, including setup instructions, database schema, API endpoints, and more.

### [Deployment Guide](deployment-guide.md)
Instructions for deploying the MC-Bench backend in production environments, including configuration, scaling, and monitoring.

## Quick Start

For a quick start, follow these steps:

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   # or
   make install-dev
   ```

3. Start the development environment:
   ```bash
   docker-compose up -d
   ```

4. Run the application:
   ```bash
   make build-run
   ```

## Getting Help

If you encounter any issues or have questions:

1. Check the documentation sections above
2. Look for similar issues in the project repository
3. Contact the development team

## Contributing

Contributions to the MC-Bench backend are welcome. Please ensure your code follows the established style guidelines and includes appropriate tests.