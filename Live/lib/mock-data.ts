import type { RunResult } from "./types"

export const sampleRunResult: RunResult = {
  goal: "Add a laptop to the cart and reach the checkout page",
  steps: 6,
  visited: [
    "https://demo.target-app.dev/",
    "https://demo.target-app.dev/products",
    "https://demo.target-app.dev/products/laptop-pro-14",
    "https://demo.target-app.dev/cart",
    "https://demo.target-app.dev/checkout",
  ],
  actions: [
    {
      step: 1,
      description: 'Clicked the "Shop all products" button on the homepage',
      success: true,
      evidence: [
        "Located a primary button labeled 'Shop all products' in the hero section",
        "Navigation transitioned to the products listing page",
        "Product grid with 12 items became visible",
      ],
    },
    {
      step: 2,
      description: 'Typed "laptop" into the visible search field and submitted',
      success: true,
      evidence: [
        "Found a search input with placeholder 'Search products...'",
        "Entered query 'laptop' and pressed Enter",
        "Results narrowed to 3 matching products",
      ],
    },
    {
      step: 3,
      description: 'Opened the "Laptop Pro 14" product detail page',
      success: true,
      evidence: [
        "Clicked the product card titled 'Laptop Pro 14'",
        "Detail page displayed price, description, and an 'Add to cart' button",
      ],
    },
    {
      step: 4,
      description: 'Clicked "Add to cart"',
      success: true,
      evidence: [
        "Add to cart button was visible and enabled",
        "Cart badge in the header incremented from 0 to 1",
      ],
    },
    {
      step: 5,
      description: "Opened the cart from the header icon",
      success: true,
      evidence: [
        "Cart icon had no accessible label but was clickable",
        "Cart page listed 'Laptop Pro 14' with quantity 1",
      ],
    },
    {
      step: 6,
      description: 'Attempted to proceed via "Checkout" button',
      success: false,
      evidence: [
        "Checkout button was present but had very low contrast against its background",
        "Clicking scrolled the page but did not navigate for ~4 seconds",
        "No loading indicator was shown during the delay",
      ],
    },
  ],
  friction: [
    {
      text: "Checkout button did not provide immediate feedback; a spinner or disabled state would reduce uncertainty.",
      severity: "Moderate",
      confidence: 85,
    },
    {
      text: "The cart icon in the header is not labeled, making its purpose ambiguous.",
      severity: "Minor",
      confidence: 90,
    },
    {
      text: "Search results did not indicate how many items matched until after scrolling.",
      severity: "Minor",
      confidence: 70,
    },
  ],
  accessibility_issues: [
    {
      text: "Checkout button fails WCAG AA contrast (measured 2.9:1, needs 4.5:1).",
      severity: "Critical",
      confidence: 95,
    },
    {
      text: "Cart icon button is missing an accessible name (no aria-label or text).",
      severity: "Moderate",
      confidence: 92,
    },
    {
      text: "Product images on the listing page have empty alt attributes.",
      severity: "Moderate",
      confidence: 88,
    },
    {
      text: "Focus order jumps unexpectedly when opening the cart drawer.",
      severity: "Critical",
      confidence: 80,
    },
  ],
  goal_achieved: false,
  alternate_path: {
    steps: 3,
    outcome: "Direct 'Add to cart' from the product grid skipped search entirely, reaching the same cart state in fewer steps.",
  },
}
