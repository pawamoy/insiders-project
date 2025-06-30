# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [4.1.0](https://github.com/pawamoy/insiders-project/releases/tag/4.1.0) - 2025-06-30

<small>[Compare with 4.0.2](https://github.com/pawamoy/insiders-project/compare/4.0.2...4.1.0)</small>

### Features

- Also return PRs in backlog ([89da904](https://github.com/pawamoy/insiders-project/commit/89da904bfb139d2baf6242f256eb77c8b27ec7f9) by Timothée Mazzucotelli).

## [4.0.2](https://github.com/pawamoy/insiders-project/releases/tag/4.0.2) - 2025-03-29

<small>[Compare with 4.0.1](https://github.com/pawamoy/insiders-project/compare/4.0.1...4.0.2)</small>

### Dependencies

- Depend on Cappa 0.26.3 ([ea5d5a6](https://github.com/pawamoy/insiders-project/commit/ea5d5a6b860bf17d14d36db9b48a5bb1dd772fd5) by Timothée Mazzucotelli).
- Upgrade dependencies' lower bounds ([48185e1](https://github.com/pawamoy/insiders-project/commit/48185e148913cba61c7e9e5c2ec1627e7b319825) by Timothée Mazzucotelli).

### Code Refactoring

- Use GitHub advanced query syntax ([cd31a02](https://github.com/pawamoy/insiders-project/commit/cd31a022f03f95722570d6f48b15a18eb2d8bfdb) by Timothée Mazzucotelli).

## [4.0.1](https://github.com/pawamoy/insiders-project/releases/tag/4.0.1) - 2025-03-03

<small>[Compare with 4.0.0](https://github.com/pawamoy/insiders-project/compare/4.0.0...4.0.1)</small>

### Build

- Add (missing) dependencies from pypi-insiders ([d11cfa9](https://github.com/pawamoy/insiders-project/commit/d11cfa9b69c2f2171bf8a05982e94a50a5577c43) by Timothée Mazzucotelli).

## [4.0.0](https://github.com/pawamoy/insiders-project/releases/tag/4.0.0) - 2025-03-03

<small>[Compare with 3.0.0](https://github.com/pawamoy/insiders-project/compare/3.0.0...4.0.0)</small>

### Breaking changes

- `Polar.get_issues`: *Public object was removed*
- `Backlog.SortStrategy.min_pledge`: *Public object was removed*
- `Backlog.SortStrategy.pledge`: *Public object was removed*
- `Issue.pledged`: *Public object was removed*
- `Issue.platform`: *Public object was removed*
- `Issue(pledged)`: *Parameter was removed*
- `Issue(platform)`: *Parameter was removed*
- `IssueDict`: *Public object was removed*
- `get_backlog(polar)`: *Parameter was removed*
- `get_backlog(sponsors)`: *Positional parameter was moved*
- `get_backlog(issue_labels)`: *Positional parameter was moved*

### Build

- Stop depending on pypi-insiders ([a6b2473](https://github.com/pawamoy/insiders-project/commit/a6b2473d7a4cfd42e815b2f0321fc736dee12854) by Timothée Mazzucotelli).

### Bug Fixes

- Fix checking issue funding when building backlog ([773986b](https://github.com/pawamoy/insiders-project/commit/773986b2da26cfe9f98f084adc644ff531a9c035) by Timothée Mazzucotelli).
- Fix Polar metadata key ([157ce94](https://github.com/pawamoy/insiders-project/commit/157ce9439c8c047c99e5448e5f6db94493e6ba9d) by Timothée Mazzucotelli).
- Fix in-place add for sponsors class ([4f8161f](https://github.com/pawamoy/insiders-project/commit/4f8161fbb1bf169b44940626dd9a7afa46616c52) by Timothée Mazzucotelli).

### Code Refactoring

- Synchronize API and inventory again, cleanup ([27b45d7](https://github.com/pawamoy/insiders-project/commit/27b45d7b89a1b23f4c7d80c4f473980516a7f1bd) by Timothée Mazzucotelli).
- Synchronize public API and objects inventory ([37ddd00](https://github.com/pawamoy/insiders-project/commit/37ddd000c1d69b71d20051980150a379288e931d) by Timothée Mazzucotelli).
- Remove boost feature (issue funding discontinued by Polar) ([b62d293](https://github.com/pawamoy/insiders-project/commit/b62d293dd62ba50c24f6e3aa399d0b606d9b627c) by Timothée Mazzucotelli).
- Remove unused org field on beneficiary class ([4943556](https://github.com/pawamoy/insiders-project/commit/4943556e86b46d0669211b193aec3fe441c348ef) by Timothée Mazzucotelli).

## [3.0.0](https://github.com/pawamoy/insiders-project/releases/tag/3.0.0) - 2025-02-08

Big refactoring again. Configuration and models changed in a breaking way.

<small>[Compare with 2.0.1](https://github.com/pawamoy/insiders-project/compare/2.0.1...3.0.0)</small>

### Features

- Implement `sponsors list` command ([af52d70](https://github.com/pawamoy/insiders-project/commit/af52d7038c98327ab75ef9e9003e5499bcfe9bf9) by Timothée Mazzucotelli). [Issue-2](https://github.com/pawamoy/insiders-project/issues/2), [Issue-4](https://github.com/pawamoy/insiders-project/issues/4)
- Add dry-run mode for `sponsors team-sync` command ([948d053](https://github.com/pawamoy/insiders-project/commit/948d053199ea5520c3d0380393724b948b9f128a) by Timothée Mazzucotelli).

### Code Refactoring

- Allow finer-grain logs filtering ([c86bdd5](https://github.com/pawamoy/insiders-project/commit/c86bdd536120cec021bdb732cb66a42b413547ae) by Timothée Mazzucotelli).

## [2.0.1](https://github.com/pawamoy/insiders/releases/tag/2.0.1) - 2025-01-17

<small>[Compare with 2.0.0](https://github.com/pawamoy/insiders/compare/2.0.0...2.0.1)</small>

### Bug Fixes

- Don't load config twice ([bbd7eb7](https://github.com/pawamoy/insiders/commit/bbd7eb799b15ca899b3491c00ed16dcc56ecb651) by Timothée Mazzucotelli).

## [2.0.0](https://github.com/pawamoy/insiders/releases/tag/2.0.0) - 2025-01-16

<small>[Compare with 1.0.0](https://github.com/pawamoy/insiders/compare/1.0.0...2.0.0)</small>

### Code Refactoring

This project went under a complete refactoring. It provides much more features and now integrates the [`pypi-insiders`](https://pypi.org/project/pypi-insiders/) project. Let us know what you think of our CLI!

- Format Copier answers with context ([d056e3b](https://github.com/pawamoy/insiders/commit/d056e3b0439a2e0569cf6d1557f402e6eb297987) by Timothée Mazzucotelli).
- Only warn about unknown keys ([81b65d2](https://github.com/pawamoy/insiders/commit/81b65d257b4ff552749875ebe7d2ffd287c77434) by Timothée Mazzucotelli).
- Check for unknown config keys ([a343025](https://github.com/pawamoy/insiders/commit/a343025d15f6f3eb427484a016f0c75cd8faae65) by Timothée Mazzucotelli).
- Bind more options to the config ([85729fa](https://github.com/pawamoy/insiders/commit/85729fafef8dfb8ed9089c0fbec8938a5c057cc7) by Timothée Mazzucotelli).
- Improve index class ([1da458f](https://github.com/pawamoy/insiders/commit/1da458f172730ca42e4212e5c9bc8837a0177abc) by Timothée Mazzucotelli).
- Expose interception handler and its `allow` tuple ([d2e5396](https://github.com/pawamoy/insiders/commit/d2e5396f2197ad6e1665223ee008664d1d5e5449) by Timothée Mazzucotelli).
- Improve CLI and config ([05c2704](https://github.com/pawamoy/insiders/commit/05c2704daf28c91e59f698c68f284632960d1892) by Timothée Mazzucotelli).
- Completely refactor project ([7c080a3](https://github.com/pawamoy/insiders/commit/7c080a3cd8c8e932cf7369f866cd2a68af8bad00) by Timothée Mazzucotelli).
- Add library surface ([b2be4ef](https://github.com/pawamoy/insiders/commit/b2be4ef11b17d427bec3e466cf79ad33d1e5f472) by Timothée Mazzucotelli).

## [1.0.0](https://github.com/pawamoy/insiders/releases/tag/1.0.0) - 2024-10-12

<small>[Compare with first commit](https://github.com/pawamoy/insiders/compare/625c8abf651f00fe7101ad7cfdb060805a2e172f...1.0.0)</small>

### Features

- Make the project public! ([f6b3e08](https://github.com/pawamoy/insiders/commit/f6b3e0885ffda3b0a7c835307e243580b18c83bc) by Timothée Mazzucotelli).
