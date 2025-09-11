import { danger, fail, warn, message, markdown } from 'danger';

// ==============
// Configuration
// ==============

const MAX_PR_SIZE = 500; // lines
const MIN_PR_DESCRIPTION_LENGTH = 10;
const PROTECTED_FILES = [
  'package.json',
  'pnpm-lock.yaml',
  'requirements.txt',
  'pyproject.toml',
  'docker-compose.yml',
  'infra/terraform/**',
];

// =================
// Helper Functions
// =================

const getChangedFiles = () => [
  ...danger.git.created_files,
  ...danger.git.modified_files,
  ...danger.git.deleted_files,
];

const getTotalLines = () =>
  danger.git.diffstat.insertions + danger.git.diffstat.deletions;

const hasChangesInPath = (path: string) =>
  getChangedFiles().some((file) => file.includes(path));

const getFilesByExtension = (extensions: string[]) =>
  getChangedFiles().filter((file) =>
    extensions.some((ext) => file.endsWith(ext))
  );

// =============
// PR Size Check
// =============

const checkPRSize = () => {
  const totalLines = getTotalLines();

  if (totalLines > MAX_PR_SIZE) {
    warn(
      `🚨 This PR is quite large (${totalLines} lines). Consider breaking it into smaller PRs for easier review.`
    );

    // Provide suggestions for large PRs
    const suggestions = [
      'Split refactoring from new features',
      'Separate tests from implementation changes',
      'Break down features into smaller components',
      'Consider draft PRs for work-in-progress',
    ];

    markdown(`
### 📊 Large PR Suggestions

This PR has ${totalLines} lines of changes. Here are some ways to make it more reviewable:

${suggestions.map((s) => `- ${s}`).join('\n')}
    `);
  }
};

// ==================
// PR Description Check
// ==================

const checkPRDescription = () => {
  if (danger.github.pr.body.length < MIN_PR_DESCRIPTION_LENGTH) {
    fail('❌ Please provide a detailed description of your changes.');
    return;
  }

  // Check for specific sections in description
  const body = danger.github.pr.body.toLowerCase();
  const requiredSections = ['what', 'why', 'how'];
  const missingSections = requiredSections.filter(
    (section) => !body.includes(section)
  );

  if (missingSections.length > 0) {
    warn(
      `📝 Consider adding these sections to your PR description: ${missingSections.join(', ')}`
    );
  }

  // Check for breaking changes mention
  if (body.includes('breaking') && !danger.github.pr.title.includes('!')) {
    warn(
      "🚨 Breaking changes mentioned in description but not marked in title with '!'"
    );
  }
};

// ===================
// Code Quality Checks
// ===================

const checkCodeQuality = () => {
  const pythonFiles = getFilesByExtension(['.py']);
  const jsFiles = getFilesByExtension(['.ts', '.tsx', '.js', '.jsx']);

  // Check Python files
  if (pythonFiles.length > 0) {
    message(`🐍 Python files changed: ${pythonFiles.length}`);

    // Check for common Python issues
    pythonFiles.forEach((file) => {
      // Note: In a real implementation, you'd read file contents
      // This is a placeholder for demonstration
      message(`📁 Modified Python file: ${file}`);
    });
  }

  // Check JavaScript/TypeScript files
  if (jsFiles.length > 0) {
    message(`📜 JavaScript/TypeScript files changed: ${jsFiles.length}`);

    jsFiles.forEach((file) => {
      message(`📁 Modified JS/TS file: ${file}`);
    });
  }
};

// ====================
// Documentation Checks
// ====================

const checkDocumentation = () => {
  const hasCodeChanges =
    getFilesByExtension(['.py', '.ts', '.tsx', '.js', '.jsx']).length > 0;
  const hasDocChanges = getFilesByExtension(['.md', '.rst']).length > 0;

  if (hasCodeChanges && !hasDocChanges) {
    warn('📚 Consider updating documentation for your code changes.');
  }

  // Check for README updates when adding new features
  if (
    danger.github.pr.title.toLowerCase().includes('feat') &&
    !hasChangesInPath('README.md')
  ) {
    warn(
      '📖 New features often need README updates. Consider documenting the new functionality.'
    );
  }
};

// ============
// Test Checks
// ============

const checkTests = () => {
  const hasCodeChanges = getFilesByExtension(['.py', '.ts', '.tsx']).length > 0;
  const hasTestChanges =
    getFilesByExtension([
      '.test.ts',
      '.test.tsx',
      '.test.py',
      '.spec.ts',
      '.spec.tsx',
      '.spec.py',
    ]).length > 0;

  if (hasCodeChanges && !hasTestChanges) {
    warn(
      '🧪 No test changes detected. Consider adding tests for your changes.'
    );
  }

  // Check for test files in proper locations
  const testFiles = getChangedFiles().filter(
    (file) =>
      file.includes('/tests/') ||
      file.includes('/__tests__/') ||
      file.includes('/test/')
  );

  if (testFiles.length > 0) {
    message(`✅ Test files modified: ${testFiles.length}`);
  }
};

// ===================
// Security Checks
// ===================

const checkSecurity = () => {
  const sensitivePatterns = [
    /password\s*=\s*["'][^"']{8,}["']/i,
    /secret\s*=\s*["'][^"']{8,}["']/i,
    /api[_-]?key\s*=\s*["'][^"']{8,}["']/i,
    /token\s*=\s*["'][^"']{8,}["']/i,
  ];

  const changedFiles = getChangedFiles();

  // Note: In a real implementation, you'd read file contents and check patterns
  // This is a placeholder warning
  if (
    changedFiles.some(
      (file) => file.includes('.env') && !file.includes('.env.example')
    )
  ) {
    fail(
      '🔒 Environment files should not be committed! Add them to .gitignore.'
    );
  }

  if (
    changedFiles.some(
      (file) => file.includes('private') || file.includes('secret')
    )
  ) {
    warn(
      "🔐 Files with 'private' or 'secret' in the name detected. Ensure no sensitive data is included."
    );
  }
};

// ======================
// Dependency Checks
// ======================

const checkDependencies = () => {
  const packageJsonChanged = hasChangesInPath('package.json');
  const lockfileChanged = hasChangesInPath('pnpm-lock.yaml');
  const requirementsChanged = hasChangesInPath('requirements.txt');
  const pyprojectChanged = hasChangesInPath('pyproject.toml');

  if (packageJsonChanged && !lockfileChanged) {
    fail(
      "📦 package.json changed but pnpm-lock.yaml wasn't updated. Run `pnpm install`."
    );
  }

  if (requirementsChanged || pyprojectChanged) {
    message(
      '🐍 Python dependencies changed. Ensure virtual environment is updated.'
    );
  }

  // Check for major version bumps
  if (packageJsonChanged) {
    warn('📦 Package.json modified. Review dependency changes carefully.');
  }
};

// ====================
// Infrastructure Checks
// ====================

const checkInfrastructure = () => {
  if (hasChangesInPath('infra/terraform/')) {
    warn(
      '🏗️ Infrastructure changes detected. Ensure proper review and testing.'
    );
    message('🧪 Consider running `terraform plan` to preview changes.');
  }

  if (
    hasChangesInPath('docker-compose.yml') ||
    hasChangesInPath('Dockerfile')
  ) {
    warn(
      '🐳 Docker configuration changed. Test locally and update documentation if needed.'
    );
  }

  if (hasChangesInPath('.github/workflows/')) {
    warn(
      '⚙️ CI/CD workflows modified. Test changes carefully to avoid breaking builds.'
    );
  }
};

// ===================
// Title and Labels
// ===================

const checkTitleAndLabels = () => {
  const title = danger.github.pr.title;
  const labels = danger.github.pr.labels.map((label) => label.name);

  // Check conventional commit format in title
  const conventionalPattern =
    /^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?: .+/;

  if (!conventionalPattern.test(title)) {
    warn(
      '📝 PR title should follow conventional commit format: `type(scope): description`'
    );
  }

  // Suggest labels based on changes
  const suggestedLabels = [];

  if (hasChangesInPath('services/')) suggestedLabels.push('backend');
  if (hasChangesInPath('web/') || hasChangesInPath('dashboard/'))
    suggestedLabels.push('frontend');
  if (hasChangesInPath('infra/')) suggestedLabels.push('infrastructure');
  if (getFilesByExtension(['.test.', '.spec.']).length > 0)
    suggestedLabels.push('tests');
  if (getFilesByExtension(['.md']).length > 0)
    suggestedLabels.push('documentation');

  const missingLabels = suggestedLabels.filter(
    (label) => !labels.includes(label)
  );

  if (missingLabels.length > 0) {
    message(`🏷️ Consider adding these labels: ${missingLabels.join(', ')}`);
  }
};

// ==================
// Performance Checks
// ==================

const checkPerformance = () => {
  const largeFiles = getChangedFiles().filter((file) => {
    // In a real implementation, you'd check actual file sizes
    return file.includes('large') || file.includes('bundle');
  });

  if (largeFiles.length > 0) {
    warn(
      `📈 Large files detected: ${largeFiles.join(', ')}. Consider optimization.`
    );
  }

  // Check for potential performance issues
  if (hasChangesInPath('services/api/')) {
    message(
      '🔍 API changes detected. Consider performance impact on endpoints.'
    );
  }
};

// ================
// Review Reminders
// ================

const addReviewReminders = () => {
  const changeTypes = [];

  if (hasChangesInPath('services/')) changeTypes.push('Backend');
  if (hasChangesInPath('web/') || hasChangesInPath('dashboard/'))
    changeTypes.push('Frontend');
  if (hasChangesInPath('infra/')) changeTypes.push('Infrastructure');

  if (changeTypes.length > 1) {
    message(
      `🔄 This PR touches multiple areas: ${changeTypes.join(', ')}. Consider requesting reviews from relevant team members.`
    );
  }

  // Add checklist for reviewers
  if (getTotalLines() > 100) {
    markdown(`
### 📋 Reviewer Checklist

- [ ] Code follows project conventions and standards
- [ ] Tests cover the new functionality/changes
- [ ] Documentation is updated where necessary
- [ ] No sensitive information is exposed
- [ ] Performance implications considered
- [ ] Breaking changes are properly documented
    `);
  }
};

// ==============
// Main Execution
// ==============

// Basic PR checks
checkPRSize();
checkPRDescription();
checkTitleAndLabels();

// Code quality and standards
checkCodeQuality();
checkTests();
checkDocumentation();

// Security and dependencies
checkSecurity();
checkDependencies();

// Infrastructure and deployment
checkInfrastructure();

// Performance considerations
checkPerformance();

// Review assistance
addReviewReminders();

// Final summary
const changedFiles = getChangedFiles();
const totalLines = getTotalLines();

markdown(`
---
## 📊 PR Summary

- **Files changed:** ${changedFiles.length}
- **Lines changed:** ${totalLines} (+${danger.git.diffstat.insertions}, -${danger.git.diffstat.deletions})
- **Commits:** ${danger.git.commits.length}

### 🔧 Changed Areas
${hasChangesInPath('services/') ? '- 🔧 Backend Services\n' : ''}${hasChangesInPath('web/') || hasChangesInPath('dashboard/') ? '- 🎨 Frontend Applications\n' : ''}${hasChangesInPath('infra/') ? '- 🏗️ Infrastructure\n' : ''}${hasChangesInPath('tests/') || hasChangesInPath('__tests__/') ? '- 🧪 Tests\n' : ''}${hasChangesInPath('docs/') || getFilesByExtension(['.md']).length > 0 ? '- 📚 Documentation\n' : ''}

---
`);

// Welcome message for first-time contributors
if (danger.github.pr.user.type === 'User' && danger.git.commits.length === 1) {
  message(
    '🎉 Welcome to the project! Thanks for your contribution. A maintainer will review your PR soon.'
  );
}
