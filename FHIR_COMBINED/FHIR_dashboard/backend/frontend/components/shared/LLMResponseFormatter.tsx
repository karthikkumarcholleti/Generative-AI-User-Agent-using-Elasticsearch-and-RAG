import React from 'react';

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    'Cardiovascular': 'bg-red-50 border-red-200 text-red-800',
    'Respiratory': 'bg-blue-50 border-blue-200 text-blue-800',
    'Mental Health': 'bg-purple-50 border-purple-200 text-purple-800',
    'Neurological': 'bg-indigo-50 border-indigo-200 text-indigo-800',
    'Musculoskeletal': 'bg-orange-50 border-orange-200 text-orange-800',
    'Gastrointestinal': 'bg-green-50 border-green-200 text-green-800',
    'Renal': 'bg-cyan-50 border-cyan-200 text-cyan-800',
    'Endocrine': 'bg-pink-50 border-pink-200 text-pink-800',
    'Metabolic': 'bg-yellow-50 border-yellow-200 text-yellow-800',
    'Oncology': 'bg-rose-50 border-rose-200 text-rose-800',
    'Acute': 'bg-yellow-50 border-yellow-200 text-yellow-800',
  };
  return colors[category] || 'bg-gray-50 border-gray-200 text-gray-800';
};

const getPriorityColor = (priority: string): string => {
  const colors: Record<string, string> = {
    'HIGH': 'bg-red-100 text-red-800 border-red-200',
    'MEDIUM': 'bg-yellow-100 text-yellow-800 border-yellow-200',
    'LOW': 'bg-green-100 text-green-800 border-green-200',
  };
  return colors[priority] || 'bg-gray-100 text-gray-800 border-gray-200';
};

const ABNORMAL_RE = /(abnormal|concerning|high|low|elevated|critical|diabetic|prediabetic)/i;

export function formatLLMResponse(text: string): React.ReactNode {
  if (!text) return null;

  const formatted: React.ReactNode[] = [];

  text.split('\n').forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      formatted.push(<br key={`br-${index}`} />);
      return;
    }

    // Category header: "CARDIOVASCULAR:"
    const categoryMatch = trimmed.match(/^([A-Z\s]+):\s*$/);
    if (categoryMatch) {
      const category = categoryMatch[1].trim();
      formatted.push(
        <div key={`cat-${index}`} className="mt-4 mb-2">
          <span className={`inline-block px-3 py-1 rounded-lg text-sm font-semibold border ${getCategoryColor(category)}`}>
            {category}
          </span>
        </div>
      );
      return;
    }

    // Priority line: "🔴 HIGH: ..."
    const priorityMatch = trimmed.match(/^([🔴🟡🟢])\s*(HIGH|MEDIUM|LOW):\s*(.+)$/);
    if (priorityMatch) {
      const [, , priority, content] = priorityMatch;
      formatted.push(
        <div key={`pri-${index}`} className="flex items-start gap-2 py-1 pl-4">
          <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getPriorityColor(priority)}`}>
            {priority}
          </span>
          <span className="text-slate-700 flex-1">{content}</span>
        </div>
      );
      return;
    }

    // Numbered list: "1. ..."
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      const [, num, content] = numberedMatch;
      formatted.push(
        <div key={`num-${index}`} className="flex gap-3 py-1">
          <span className="text-sidebar-accent font-semibold flex-shrink-0">{num}.</span>
          <span className={ABNORMAL_RE.test(content) ? 'text-rose-600 font-medium' : 'text-slate-700'}>{content}</span>
        </div>
      );
      return;
    }

    // Bullet: "- ..." or "• ..."
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      const content = trimmed.substring(2);
      formatted.push(
        <div key={`bul-${index}`} className="flex gap-3 py-1">
          <span className="text-sidebar-accent flex-shrink-0">•</span>
          <span className={ABNORMAL_RE.test(content) ? 'text-rose-600 font-medium' : 'text-slate-700'}>{content}</span>
        </div>
      );
      return;
    }

    formatted.push(
      <p key={`p-${index}`} className={ABNORMAL_RE.test(trimmed) ? 'text-rose-600 font-medium py-1' : 'text-slate-700 py-1'}>
        {trimmed}
      </p>
    );
  });

  return <div className="space-y-1">{formatted}</div>;
}
