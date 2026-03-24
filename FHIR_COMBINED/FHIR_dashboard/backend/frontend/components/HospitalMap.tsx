'use client';

import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';
import { GoogleMap, Marker, InfoWindow } from '@react-google-maps/api';

type HospitalLocation = {
  id: number;
  hospital_name: string;
  city: string;
  state: string;
  postal_code: string;
  latitude: string;  
  longitude: string;
};

const containerStyle = { width: '100%', height: '600px' };

const defaultCenter = { lat: 46.5, lng: -87.5 }; 

export default function HospitalMap() {
  const [locations, setLocations] = useState<HospitalLocation[]>([]);
  const [activeKey, setActiveKey] = useState<string | null>(null); // "lat,lng"
  const [selectedHospital, setSelectedHospital] = useState<string>(''); // hospital_name
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);

  // Load locations from API
  useEffect(() => {
    console.log('🔄 Fetching hospital locations...');
    setLoading(true);
    setError(null);
    
    axios
      .get<HospitalLocation[]>('http://localhost:5000/api/locations')
      .then((res) => {
        console.log('✅ Hospital locations loaded:', res.data?.length || 0, 'locations');
        console.log('📍 Sample location:', res.data?.[0]);
        setLocations(res.data || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error('❌ Failed to load hospital locations:', err);
        console.error('Error details:', err.response?.data || err.message);
        setError(err.response?.data?.error || err.message || 'Failed to load hospital locations');
        setLoading(false);
      });
  }, []);

  // Build unique hospital list + display label "Hospital (City, State)"
  const { uniqueHospitals, hospitalDisplay } = useMemo(() => {
    const names = new Set<string>();
    const display: Record<string, string> = {};
    for (const loc of locations) {
      const name = (loc.hospital_name || '').trim();
      if (!name) continue;
      if (!names.has(name)) {
        names.add(name);
        display[name] = `${name} (${loc.city}, ${loc.state})`;
      }
    }
    return {
      uniqueHospitals: Array.from(names).sort((a, b) => a.localeCompare(b)),
      hospitalDisplay: display,
    };
  }, [locations]);

  // Group markers by lat,lng so multiple rows at the same point share one marker
  const markerGroups: Record<string, HospitalLocation[]> = useMemo(() => {
    const groups: Record<string, HospitalLocation[]> = {};
    let validLocations = 0;
    let invalidLocations = 0;
    
    for (const loc of locations) {
      const lat = parseFloat(loc.latitude);
      const lng = parseFloat(loc.longitude);
      if (Number.isNaN(lat) || Number.isNaN(lng)) {
        invalidLocations++;
        console.warn('⚠️ Invalid coordinates for:', loc.hospital_name, 'lat:', loc.latitude, 'lng:', loc.longitude);
        continue;
      }
      validLocations++;
      const key = `${lat},${lng}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(loc);
    }
    
    console.log(`📍 Marker groups: ${Object.keys(groups).length} unique locations`);
    console.log(`✅ Valid locations: ${validLocations}, ❌ Invalid: ${invalidLocations}`);
    
    return groups;
  }, [locations]);

  // Fit bounds to all markers on initial load
  const onMapLoad = useCallback(
    (map: google.maps.Map) => {
      mapRef.current = map;
      const bounds = new window.google.maps.LatLngBounds();
      for (const key of Object.keys(markerGroups)) {
        const [lat, lng] = key.split(',').map(parseFloat);
        if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
          bounds.extend({ lat, lng });
        }
      }
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
      } else {
        map.setCenter(defaultCenter);
        map.setZoom(6);
      }
    },
    [markerGroups]
  );

  // Auto-zoom to selected hospital
  useEffect(() => {
    if (!mapRef.current || !selectedHospital) return;

    const matchedPoints = Object.entries(markerGroups).filter(([, group]) =>
      group.some((g) => g.hospital_name === selectedHospital)
    );

    if (matchedPoints.length === 0) return;

    const bounds = new window.google.maps.LatLngBounds();
    for (const [key] of matchedPoints) {
      const [lat, lng] = key.split(',').map(parseFloat);
      if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
        bounds.extend({ lat, lng });
      }
    }
    mapRef.current.fitBounds(bounds);
  }, [selectedHospital, markerGroups]);

  return (
    <>
      {/* Status Display */}
      {loading && (
        <div className="mb-4 p-4 bg-blue-100 border border-blue-300 rounded">
          <p className="text-blue-800">🔄 Loading hospital locations...</p>
        </div>
      )}
      
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-300 rounded">
          <p className="text-red-800">❌ Error: {error}</p>
        </div>
      )}
      
      {!loading && !error && locations.length === 0 && (
        <div className="mb-4 p-4 bg-yellow-100 border border-yellow-300 rounded">
          <p className="text-yellow-800">⚠️ No hospital locations found</p>
        </div>
      )}

      {/* Filter by unique hospital name */}
      <div className="flex flex-col md:flex-row justify-between items-center mb-4 gap-4">
        <select
          className="border rounded px-4 py-2 text-sm w-full md:w-1/2"
          value={selectedHospital}
          onChange={(e) => {
            setSelectedHospital(e.target.value);
            setActiveKey(null);
          }}
          disabled={loading || !!error || locations.length === 0}
        >
          <option value="">-- Filter by Hospital ({uniqueHospitals.length} hospitals) --</option>
          {uniqueHospitals.map((name) => (
            <option key={name} value={name}>
              {hospitalDisplay[name] || name}
            </option>
          ))}
        </select>
      </div>

      <GoogleMap
        mapContainerStyle={containerStyle}
        center={defaultCenter}
        zoom={6}
        mapTypeId="roadmap"
        onLoad={onMapLoad}
        onClick={() => setActiveKey(null)}
      >
        {/* Markers */}
        {Object.entries(markerGroups).map(([key, group]) => {
          const [lat, lng] = key.split(',').map(parseFloat);
          if (Number.isNaN(lat) || Number.isNaN(lng)) return null;

          const isHighlighted =
            !!selectedHospital && group.some((g) => g.hospital_name === selectedHospital);

          return (
            <Marker
              key={key}
              position={{ lat, lng }}
              icon={{
                url: isHighlighted
                  ? 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                  : 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                scaledSize: new window.google.maps.Size(36, 36),
              }}
              onMouseOver={() => setActiveKey(key)}
              onClick={() => setActiveKey(key)}
            />
          );
        })}

        {/* InfoWindow: Hospital Name + City, State */}
        {activeKey && markerGroups[activeKey] && (
          <InfoWindow
            position={{
              lat: parseFloat(activeKey.split(',')[0]),
              lng: parseFloat(activeKey.split(',')[1]),
            }}
            onCloseClick={() => setActiveKey(null)}
          >
            <div className="text-sm text-gray-800 max-w-xs">
              <p className="font-bold mb-1">
                {markerGroups[activeKey][0].hospital_name}
              </p>
              <p className="text-sm text-gray-600">
                {markerGroups[activeKey][0].city}, {markerGroups[activeKey][0].state}
              </p>
            </div>
          </InfoWindow>
        )}
      </GoogleMap>
    </>
  );
}
