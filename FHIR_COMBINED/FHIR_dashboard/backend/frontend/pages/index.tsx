import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/redux/hooks';
import { fetchAverageAge, fetchSummaryStats } from '@/redux/statsSlice';
import DashboardCard from '@/components/DashboardCard';
import Sidebar from '@/components/Sidebar';
import DashboardCharts from '@/components/DashboardCharts';
import HospitalMap from '@/components/HospitalMap';
import MapProvider from '@/components/MapProvider';

export default function Home() {
  const dispatch = useAppDispatch();
  const { averageAge, loading, error, summary } = useAppSelector((state) => state.stats);

  useEffect(() => {
    dispatch(fetchAverageAge());
    dispatch(fetchSummaryStats());
  }, [dispatch]);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 p-8 bg-gray-100 space-y-10">
        <h1 className="text-3xl font-bold mb-6">FHIR Dashboard</h1>

        {/* Top Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <DashboardCard title="Patients" value={summary?.patients ?? '...'} />
          <DashboardCard title="Observations" value={summary?.observations ?? '...'} />
          <DashboardCard title="Conditions" value={summary?.conditions ?? '...'} />
          <DashboardCard title="Encounters" value={summary?.encounters ?? '...'} />
        </div>

        {/* Charts Section */}
        <DashboardCharts />

        {/* Hospital Map */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Hospital Locations Map</h2>
          <MapProvider>
            <HospitalMap />
          </MapProvider>
        </div>
      </main>
    </div>
  );
}
