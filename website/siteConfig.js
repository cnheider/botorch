/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// See https://docusaurus.io/docs/site-config for all the possible
// site configuration options.

// List of projects/orgs using your project for the users page.
const users = [
];

const siteConfig = {
  title: 'botorch',
  tagline: 'Bayesian Optimization in PyTorch',
  url: 'http://botorch.io',
  baseUrl: '/', // Base URL for your project */
  // For github.io type URLs, you would set the url and baseUrl like:
  //   url: 'https://facebook.github.io',
  //   baseUrl: '/test-site/',

  // Used for publishing and more
  projectName: 'botorch',
  organizationName: 'facebookexternal',

  headerLinks: [
    {doc: 'philosophy', label: 'About'},
    {doc: 'installation', label: 'Docs'},
    {blog: true, label: 'Blog'},
    // Search can be enabled when site is online and indexed
    // {search: true},
    {href: 'https://github.com/facebookexternal/botorch', label: "GitHub" }
  ],

  // If you have users set above, you add it here:
  users,

  /* path to images for header/footer */
  headerIcon: null,
  footerIcon: null,
  favicon: null,

  /* Colors for website */
  colors: {
    primaryColor: '#f29837', // orange
    secondaryColor: '#f0bc40', // yellow
  },

  highlight: {
    theme: 'default',
  },

  // Add custom scripts here that would be placed in <script> tags.
  scripts: ['https://buttons.github.io/buttons.js'],

  // On page navigation for the current documentation page.
  onPageNav: 'separate',
  // No .html extensions for paths.
  cleanUrl: true,

  // Open Graph and Twitter card images.
  ogImage: 'img/docusaurus.png',
  twitterImage: 'img/docusaurus.png',

  // Show documentation's last contributor's name.
  // enableUpdateBy: true,

  // Show documentation's last update time.
  // enableUpdateTime: true,

};

module.exports = siteConfig;
