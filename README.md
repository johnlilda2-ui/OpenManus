<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

English | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md)

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# OpenManus + Operational AI App Platform

This fork preserves the OpenManus agent engine and adds a durable operational platform for projects, tasks, workflows, memory, approvals, isolated execution, artifacts, and AI-powered application generation.

## Builders

### Full App Builder

Generate full-stack applications through a durable workflow covering requirements, backend, frontend, integration, sandbox preview, automated testing, browser verification, autonomous repair, re-verification, and final release review.

### Website Builder

Website Builder is a specialized mode for business websites, landing pages, blogs, portfolios, marketing sites, documentation, and responsive multi-page experiences. It adds a website-specific design system and content/section/asset manifests, SEO/accessibility/performance hardening, sandbox preview, browser visual verification, deterministic screenshot similarity scoring, and targeted section iteration.

Website Builder can:

- generate `DESIGN_SYSTEM.json` with semantic design tokens and reusable component rules
- generate `SECTION_MANIFEST.json` with stable section IDs
- generate `ASSET_MANIFEST.json` for planned images/icons/media and their accessibility metadata
- run the site inside the isolated sandbox and expose a live preview
- verify representative pages in a real browser
- record a deterministic visual snapshot hash
- repair reproducible issues automatically
- compare the post-repair screenshot against the baseline with a visual similarity/diff score
- regenerate one selected section without rebuilding unrelated sections
- package the completed site as `application.zip`

A dedicated Website Builder workspace is available at `/website-builder` after authentication.

## Platform services

The platform adds JWT authentication, PostgreSQL/SQLite persistence, Redis queues, tenant roles, project-scoped tool policies, durable approvals, isolated Daytona execution, persistent memory/knowledge, durable artifacts, quotas, usage accounting, live SSE events, and a web console.

## Important boundary

Live AI generation still requires a configured LLM provider. Production sandbox/browser execution requires a configured isolated Daytona environment. Do not commit provider credentials to the repository.

## Upstream OpenManus

This project is based on the upstream OpenManus repository from FoundationAgents. See the upstream project for the original installation, browser automation and agent-engine documentation.
