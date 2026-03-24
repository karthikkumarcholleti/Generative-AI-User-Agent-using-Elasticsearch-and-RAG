'use client';

import React from 'react';
import { useJsApiLoader } from '@react-google-maps/api';
import type { Libraries } from '@react-google-maps/api';

type Props = {
  children: React.ReactNode;
};

const libraries: Libraries = ['places', 'maps', 'visualization'];

const loaderOptions: Parameters<typeof useJsApiLoader>[0] = {
  id: 'google-maps-script-loader',
  googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
  libraries,
};

export default function MapProvider({ children }: Props) {
  const { isLoaded } = useJsApiLoader(loaderOptions);

  if (!isLoaded) return <div>Loading Map...</div>;

  return <>{children}</>;
}
