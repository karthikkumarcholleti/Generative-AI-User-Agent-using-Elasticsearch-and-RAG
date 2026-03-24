import Sidebar from '@/components/Sidebar';
import PatientMetrics from '@/components/PatientMetrics';

export default function MetricsPage() {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6">
        <PatientMetrics />
      </main>
    </div>
  );
}
