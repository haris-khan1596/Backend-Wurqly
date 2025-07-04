# Contributing to Hubstaff Backend API

Thank you for considering contributing to the Hubstaff Backend API! We welcome contributions from the community and are excited to see what you'll bring to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and professional in all interactions.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with the following information:
- A clear and descriptive title
- A detailed description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Screenshots or code examples if applicable
- Your environment details (OS, Python version, etc.)

### Suggesting Enhancements

For feature requests or enhancements:
- Use the feature request template
- Provide a clear description of the enhancement
- Explain why this feature would be useful
- Include examples or mockups if possible

### Code Contributions

1. **Fork the repository** and create your branch from `main`
2. **Set up your development environment** following the README instructions
3. **Make your changes** following our coding standards
4. **Add tests** for your changes
5. **Ensure tests pass** by running the test suite
6. **Update documentation** if necessary
7. **Create a pull request** with a clear description

### Development Workflow

1. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/hubstaff-backend-api.git
   cd hubstaff-backend-api
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** and commit them:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub

### Coding Standards

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused
- Use type hints where appropriate
- Write comprehensive tests for new features

### Commit Message Format

We use conventional commits. Format your commit messages as:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Testing

- Write unit tests for all new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Use pytest for testing

Run tests with:
```bash
pytest
```

### Documentation

- Update README.md if you change functionality
- Add docstrings to new functions and classes
- Update API documentation if you change endpoints
- Include examples in your documentation

### Pull Request Process

1. **Fill out the PR template** completely
2. **Link any related issues** in your PR description
3. **Ensure CI passes** (tests, linting, etc.)
4. **Request review** from maintainers
5. **Address feedback** promptly
6. **Keep your branch up to date** with main

### Review Process

- All submissions require review from maintainers
- We may suggest changes or improvements
- Please be responsive to feedback
- PRs may be closed if inactive for extended periods

### Getting Help

If you need help:
- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Reach out to maintainers
- Join our community chat (if available)

## Recognition

Contributors will be acknowledged in our README and release notes. Thank you for helping make this project better!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
