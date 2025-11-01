/**
 * Shimmering skeleton loader that mimics a landing page structure
 * Shows while the landing page is being generated
 * Changes to random design every 7 seconds
 */

import { useState, useEffect } from "react";

// Skeleton variation 1: Standard layout
const SkeletonV1 = () => (
  <div className="h-full w-full bg-gray-50 overflow-hidden">
    {/* Header Skeleton */}
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="h-10 w-32 bg-gray-200 rounded animate-shimmer" />
          {/* Navigation */}
          <div className="flex gap-6">
            <div className="h-6 w-16 bg-gray-200 rounded animate-shimmer" />
            <div className="h-6 w-16 bg-gray-200 rounded animate-shimmer" />
            <div className="h-6 w-16 bg-gray-200 rounded animate-shimmer" />
            <div className="h-6 w-16 bg-gray-200 rounded animate-shimmer" />
          </div>
        </div>
      </div>
    </div>

    {/* Hero Section Skeleton */}
    <div className="relative bg-gradient-to-br from-gray-100 to-gray-200">
      <div className="max-w-7xl mx-auto px-6 py-20">
        <div className="max-w-3xl">
          {/* Hero Title */}
          <div className="h-12 w-3/4 bg-gray-300 rounded mb-4 animate-shimmer" />
          <div className="h-12 w-2/3 bg-gray-300 rounded mb-6 animate-shimmer" />
          {/* Hero Description */}
          <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
          <div className="h-4 w-5/6 bg-gray-200 rounded mb-2 animate-shimmer" />
          <div className="h-4 w-4/6 bg-gray-200 rounded mb-8 animate-shimmer" />
          {/* CTA Button */}
          <div className="h-12 w-48 bg-gray-300 rounded animate-shimmer" />
        </div>
      </div>
      {/* Hero Image Placeholder */}
      <div className="w-full h-96 bg-gray-300 mt-8 animate-shimmer" />
    </div>

    {/* Content Sections */}
    <div className="max-w-7xl mx-auto px-6 py-16">
      {/* Section 1 */}
      <div className="mb-16">
        <div className="text-center mb-12">
          <div className="h-8 w-64 bg-gray-300 rounded mx-auto mb-4 animate-shimmer" />
          <div className="h-4 w-96 bg-gray-200 rounded mx-auto animate-shimmer" />
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-lg p-6 shadow-sm">
              <div className="h-48 w-full bg-gray-200 rounded mb-4 animate-shimmer" />
              <div className="h-6 w-3/4 bg-gray-300 rounded mb-3 animate-shimmer" />
              <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
              <div className="h-4 w-5/6 bg-gray-200 rounded animate-shimmer" />
            </div>
          ))}
        </div>
      </div>

      {/* Section 2 - Two Column */}
      <div className="mb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="h-64 w-full bg-gray-200 rounded animate-shimmer" />
          </div>
          <div>
            <div className="h-8 w-3/4 bg-gray-300 rounded mb-4 animate-shimmer" />
            <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
            <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
            <div className="h-4 w-5/6 bg-gray-200 rounded mb-6 animate-shimmer" />
            <div className="h-10 w-40 bg-gray-300 rounded animate-shimmer" />
          </div>
        </div>
      </div>

      {/* Section 3 - Testimonials/Reviews */}
      <div className="mb-16">
        <div className="text-center mb-12">
          <div className="h-8 w-56 bg-gray-300 rounded mx-auto mb-4 animate-shimmer" />
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white rounded-lg p-6 shadow-sm border border-gray-200"
            >
              <div className="flex items-center mb-4">
                <div className="h-12 w-12 bg-gray-200 rounded-full mr-4 animate-shimmer" />
                <div>
                  <div className="h-4 w-32 bg-gray-300 rounded mb-2 animate-shimmer" />
                  <div className="h-3 w-24 bg-gray-200 rounded animate-shimmer" />
                </div>
              </div>
              <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
              <div className="h-4 w-5/6 bg-gray-200 rounded animate-shimmer" />
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Footer Skeleton */}
    <div className="bg-gray-900 mt-16">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i}>
              <div className="h-5 w-24 bg-gray-700 rounded mb-4 animate-shimmer" />
              <div className="space-y-2">
                <div className="h-4 w-20 bg-gray-800 rounded animate-shimmer" />
                <div className="h-4 w-20 bg-gray-800 rounded animate-shimmer" />
                <div className="h-4 w-20 bg-gray-800 rounded animate-shimmer" />
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-gray-800 pt-8">
          <div className="h-4 w-64 bg-gray-800 rounded mx-auto animate-shimmer" />
        </div>
      </div>
    </div>
  </div>
);

// Skeleton variation 2: Minimalist layout
const SkeletonV2 = () => (
  <div className="h-full w-full bg-white overflow-hidden">
    {/* Simple Header */}
    <div className="bg-gray-50 border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between">
          <div className="h-8 w-40 bg-gray-200 rounded animate-shimmer" />
          <div className="flex gap-4">
            <div className="h-5 w-12 bg-gray-200 rounded animate-shimmer" />
            <div className="h-5 w-12 bg-gray-200 rounded animate-shimmer" />
            <div className="h-5 w-12 bg-gray-200 rounded animate-shimmer" />
          </div>
        </div>
      </div>
    </div>

    {/* Full-width Hero */}
    <div className="bg-gray-100">
      <div className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center">
          <div className="h-16 w-2/3 bg-gray-300 rounded mx-auto mb-6 animate-shimmer" />
          <div className="h-5 w-1/2 bg-gray-200 rounded mx-auto mb-8 animate-shimmer" />
          <div className="h-14 w-56 bg-gray-300 rounded mx-auto animate-shimmer" />
        </div>
      </div>
      <div className="h-[500px] w-full bg-gray-200 animate-shimmer" />
    </div>

    {/* Grid Content */}
    <div className="max-w-6xl mx-auto px-6 py-20">
      <div className="grid md:grid-cols-2 gap-8 mb-12">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-8">
            <div className="h-40 w-full bg-gray-200 rounded mb-4 animate-shimmer" />
            <div className="h-6 w-2/3 bg-gray-300 rounded mb-3 animate-shimmer" />
            <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
            <div className="h-4 w-4/5 bg-gray-200 rounded animate-shimmer" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Skeleton variation 3: Magazine-style layout
const SkeletonV3 = () => (
  <div className="h-full w-full bg-gray-50 overflow-hidden">
    {/* Header with Logo and Search */}
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-6 py-5">
        <div className="flex items-center justify-between mb-4">
          <div className="h-10 w-36 bg-gray-200 rounded animate-shimmer" />
          <div className="h-8 w-64 bg-gray-200 rounded animate-shimmer" />
        </div>
        <div className="flex gap-8">
          <div className="h-5 w-20 bg-gray-200 rounded animate-shimmer" />
          <div className="h-5 w-20 bg-gray-200 rounded animate-shimmer" />
          <div className="h-5 w-20 bg-gray-200 rounded animate-shimmer" />
          <div className="h-5 w-20 bg-gray-200 rounded animate-shimmer" />
        </div>
      </div>
    </div>

    {/* Large Hero Image */}
    <div className="h-[600px] w-full bg-gray-200 animate-shimmer mb-16" />

    {/* Article-style Content */}
    <div className="max-w-4xl mx-auto px-6">
      <div className="mb-8">
        <div className="h-10 w-3/4 bg-gray-300 rounded mb-4 animate-shimmer" />
        <div className="h-5 w-1/2 bg-gray-200 rounded mb-6 animate-shimmer" />
        <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
        <div className="h-4 w-full bg-gray-200 rounded mb-2 animate-shimmer" />
        <div className="h-4 w-5/6 bg-gray-200 rounded mb-6 animate-shimmer" />
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-16">
        {[1, 2, 3].map((i) => (
          <div key={i}>
            <div className="h-48 w-full bg-gray-200 rounded mb-3 animate-shimmer" />
            <div className="h-5 w-full bg-gray-300 rounded mb-2 animate-shimmer" />
            <div className="h-4 w-4/5 bg-gray-200 rounded animate-shimmer" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Skeleton variation 4: Dashboard-style layout
const SkeletonV4 = () => (
  <div className="h-full w-full bg-gray-100 overflow-hidden">
    {/* Top Bar */}
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="h-8 w-28 bg-gray-200 rounded animate-shimmer" />
        <div className="flex gap-3">
          <div className="h-9 w-9 bg-gray-200 rounded-full animate-shimmer" />
          <div className="h-9 w-24 bg-gray-200 rounded animate-shimmer" />
        </div>
      </div>
    </div>

    {/* Stats Cards */}
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg p-6 shadow-sm">
            <div className="h-4 w-20 bg-gray-200 rounded mb-3 animate-shimmer" />
            <div className="h-8 w-24 bg-gray-300 rounded animate-shimmer" />
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-6">
        <div className="md:col-span-2 bg-white rounded-lg p-6 shadow-sm">
          <div className="h-6 w-32 bg-gray-300 rounded mb-4 animate-shimmer" />
          <div className="h-64 w-full bg-gray-200 rounded animate-shimmer" />
        </div>
        <div className="bg-white rounded-lg p-6 shadow-sm">
          <div className="h-6 w-28 bg-gray-300 rounded mb-4 animate-shimmer" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-12 w-12 bg-gray-200 rounded-full animate-shimmer" />
                <div className="flex-1">
                  <div className="h-4 w-3/4 bg-gray-300 rounded mb-2 animate-shimmer" />
                  <div className="h-3 w-1/2 bg-gray-200 rounded animate-shimmer" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

// Skeleton variation 5: E-commerce layout
const SkeletonV5 = () => (
  <div className="h-full w-full bg-white overflow-hidden">
    {/* Navigation Bar */}
    <div className="bg-white border-b border-gray-200 sticky top-0">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="h-9 w-32 bg-gray-200 rounded animate-shimmer" />
          <div className="flex gap-8">
            <div className="h-5 w-16 bg-gray-200 rounded animate-shimmer" />
            <div className="h-5 w-16 bg-gray-200 rounded animate-shimmer" />
            <div className="h-5 w-16 bg-gray-200 rounded animate-shimmer" />
          </div>
          <div className="h-8 w-8 bg-gray-200 rounded animate-shimmer" />
        </div>
      </div>
    </div>

    {/* Banner */}
    <div className="h-80 w-full bg-gray-200 animate-shimmer mb-12" />

    {/* Product Grid */}
    <div className="max-w-7xl mx-auto px-6">
      <div className="mb-6">
        <div className="h-7 w-40 bg-gray-300 rounded animate-shimmer" />
      </div>
      <div className="grid md:grid-cols-4 gap-6 mb-12">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="bg-gray-50 rounded-lg overflow-hidden">
            <div className="h-64 w-full bg-gray-200 animate-shimmer" />
            <div className="p-4">
              <div className="h-5 w-full bg-gray-300 rounded mb-2 animate-shimmer" />
              <div className="h-4 w-2/3 bg-gray-200 rounded mb-3 animate-shimmer" />
              <div className="h-6 w-20 bg-gray-300 rounded animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Array of all skeleton variations
const skeletonVariations = [
  SkeletonV1,
  SkeletonV2,
  SkeletonV3,
  SkeletonV4,
  SkeletonV5,
];

function LandingPageSkeleton() {
  const [currentVariant, setCurrentVariant] = useState(() =>
    Math.floor(Math.random() * skeletonVariations.length)
  );

  useEffect(() => {
    const interval = setInterval(() => {
      // Pick a random variant different from current
      let newVariant;
      do {
        newVariant = Math.floor(Math.random() * skeletonVariations.length);
      } while (newVariant === currentVariant && skeletonVariations.length > 1);

      setCurrentVariant(newVariant);
    }, 20000); // Change every 20 seconds

    return () => clearInterval(interval);
  }, [currentVariant]);

  const SkeletonComponent = skeletonVariations[currentVariant] as () => JSX.Element;

  return (
    <div className="relative h-full w-full">
      {/* Skeleton Background */}
      <div className="h-full w-full">
        <SkeletonComponent />
      </div>
      {/* Centered Message Overlay */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="bg-white/90 backdrop-blur-sm px-8 py-4 rounded-lg shadow-lg">
          <p className="text-gray-600 text-lg font-medium">
            Building your landing page... This may take a moment.
          </p>
        </div>
      </div>
    </div>
  );
}

export default LandingPageSkeleton;
