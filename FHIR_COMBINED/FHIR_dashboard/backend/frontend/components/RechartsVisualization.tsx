import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  ReferenceLine,
  ReferenceArea,
  Brush,
  Label,
} from 'recharts';
import { motion } from 'framer-motion';
import PremiumChartCard from './PremiumChartCard';
import type { ChartPayload } from '@/services/llmApi';

// Full stack team's exact color palette (matching DashboardCharts.tsx)
const PIE_COLORS = ['#0EA5E9', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];
const BAR_COLORS = ['#0EA5E9'];

// Medical color scheme (matching PatientMetrics.jsx)
const MEDICAL_COLORS: Record<string, string> = {
  heart_rate: '#0EA5E9',     // Sky Blue
  'heart rate': '#0EA5E9',
  pulse: '#0EA5E9',
  hr: '#0EA5E9',
  resp_rate: '#10B981',      // Green
  'respiratory rate': '#10B981',
  respiratory: '#10B981',
  bmi: '#F59E0B',            // Amber
  'body mass index': '#F59E0B',
  bp_sys: '#8B5CF6',         // Purple
  systolic: '#8B5CF6',
  'systolic bp': '#8B5CF6',
  bp_dia: '#EF4444',         // Red
  diastolic: '#EF4444',
  'diastolic bp': '#EF4444',
  oxygen: '#06B6D4',         // Cyan
  'oxygen saturation': '#06B6D4',
  spo2: '#06B6D4',
  glucose: '#EF4444',        // Red (for glucose)
  'blood sugar': '#EF4444',
  'glucose (mg/dl)': '#EF4444',
  blood_pressure: '#8B5CF6', // Purple
  'blood pressure': '#8B5CF6',
  bp: '#8B5CF6',
};

interface RechartsVisualizationProps {
  chart: ChartPayload;
  title?: string;
}

export default function RechartsVisualization({ chart, title }: RechartsVisualizationProps) {
  // Convert Chart.js format to Recharts format
  const convertToRechartsData = (chartData: ChartPayload) => {
    if (!chartData.data || !chartData.data.labels || !chartData.data.datasets) {
      return [];
    }

    const labels = chartData.data.labels;
    const datasets = chartData.data.datasets;

    // Create array of objects where each object represents a data point
    // { label: 'Date', dataset1: value1, dataset2: value2, ... }
    const encounterContext = (chartData as any).encounterContext || [];
    return labels.map((label, index) => {
      const dataPoint: Record<string, any> = {
        name: label,
        timestamp: label, // Keep original for date formatting
      };

      // Attach encounter context if available
      if (encounterContext[index]) {
        dataPoint._encounter = encounterContext[index];
      }

      datasets.forEach((dataset, datasetIndex) => {
        const value = dataset.data[index];
        // Use dataset label or default name
        const key = dataset.label || `Series ${datasetIndex + 1}`;
        dataPoint[key] = value !== null && value !== undefined ? value : null;
      });

      return dataPoint;
    });
  };

  const rechartsData = convertToRechartsData(chart);
  const chartType = chart.type || 'line';
  const [activeSeries, setActiveSeries] = useState<Set<string>>(new Set());

  // Get chart title from options
  const chartTitle = title || 
    (chart.options && typeof chart.options === 'object' && 'title' in chart.options
      ? (chart.options.title as any)?.text || undefined
      : undefined);

  // Determine chart type
  const isLineChart = chartType === 'line' || chartType === 'lineChart';
  const isBarChart = chartType === 'bar' || chartType === 'barChart';
  const isAreaChart = chartType === 'area' || chartType === 'areaChart';
  
  // Get datasets for rendering (must be declared before useEffect)
  const datasets = chart.data?.datasets || [];
  
  // Initialize all series as active
  React.useEffect(() => {
    if (datasets.length > 0 && activeSeries.size === 0) {
      setActiveSeries(new Set(datasets.map(d => d.label || 'default')));
    }
  }, [datasets, activeSeries.size]);

  // Format date labels if they look like dates
  const formatLabel = (label: string) => {
    if (!label) return '';
    // Try to parse as date
    const date = new Date(label);
    if (!isNaN(date.getTime())) {
      // Format as short date
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    // If it's a string that looks like a date (YYYY-MM-DD)
    if (typeof label === 'string' && /^\d{4}-\d{2}-\d{2}/.test(label)) {
      const dateStr = label.substring(0, 10);
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
    }
    return String(label);
  };

  // Enhanced tooltip formatter
  const formatTooltipValue = (value: any, name: string, payload: any) => {
    if (value === null || value === undefined) return ['N/A', name];
    
    // Find the dataset to get unit information
    const dataset = datasets.find(d => d.label === name);
    const unit = dataset?.unit || '';
    
    // Format numeric values
    if (typeof value === 'number') {
      const formatted = value.toFixed(2).replace(/\.?0+$/, '');
      return [`${formatted}${unit ? ` ${unit}` : ''}`, name];
    }
    
    return [String(value), name];
  };

  // Toggle series visibility
  const handleLegendClick = (dataKey: string) => {
    setActiveSeries(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dataKey)) {
        newSet.delete(dataKey);
      } else {
        newSet.add(dataKey);
      }
      return newSet;
    });
  };
  
  // Custom tooltip with encounter context (Gap 2)
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    const encounter = payload[0]?.payload?._encounter;
    return (
      <div style={{
        backgroundColor: 'white',
        border: '1px solid #E2E8F0',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        padding: '12px',
        maxWidth: 320,
      }}>
        <p style={{ fontWeight: 600, color: '#1E293B', marginBottom: 6, fontSize: 13 }}>
          📅 {formatLabel(label)}
        </p>
        {payload.map((entry: any, i: number) => {
          if (entry.value === null || entry.value === undefined) return null;
          const ds = datasets.find(d => d.label === entry.name);
          const unit = (ds as any)?.unit || '';
          const formatted = typeof entry.value === 'number'
            ? entry.value.toFixed(2).replace(/\.?0+$/, '')
            : String(entry.value);
          return (
            <p key={i} style={{ color: entry.color || '#475569', fontSize: 12, margin: '4px 0' }}>
              {entry.name}: <strong>{formatted}{unit ? ` ${unit}` : ''}</strong>
            </p>
          );
        })}
        {encounter && (
          <div style={{
            marginTop: 8,
            paddingTop: 6,
            borderTop: '1px solid #E2E8F0',
            fontSize: 11,
            color: '#64748B',
          }}>
            <span style={{ fontWeight: 600 }}>🏥 {encounter.encounter}</span>
            {encounter.type && <span> ({encounter.type})</span>}
            {encounter.reason && (
              <p style={{ margin: '2px 0 0', color: '#94A3B8', fontSize: 10 }}>
                {encounter.reason}
              </p>
            )}
          </div>
        )}
      </div>
    );
  };
  
  // Get reference lines from chart payload (clinical normal/critical ranges)
  const referenceLines = (chart as any).referenceLines || [];
  
  // Dual y-axis support (Gap 3+4: disease progression panels)
  const dualYAxis = (chart as any).dualYAxis as { left: { label: string; color: string }; right: { label: string; color: string } } | undefined;
  const hasDualYAxis = !!dualYAxis;

  // Handle empty data
  if (!rechartsData || rechartsData.length === 0) {
    return (
      <PremiumChartCard title={chartTitle}>
        <div className="flex items-center justify-center h-64 text-slate-500">
          <p>No data available for visualization</p>
        </div>
      </PremiumChartCard>
    );
  }

  return (
    <PremiumChartCard title={chartTitle}>
      <div className="w-full">
        <ResponsiveContainer width="100%" height={350}>
          {isAreaChart ? (
            <AreaChart data={rechartsData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
              <defs>
                {datasets.map((dataset, index) => {
                  const label = (dataset.label || '').toLowerCase().trim();
                  let color = MEDICAL_COLORS[label] || 
                             dataset.borderColor || 
                             dataset.backgroundColor || 
                             PIE_COLORS[index % PIE_COLORS.length];
                  return (
                    <linearGradient key={`gradient-${index}`} id={`gradient-${index}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={color} stopOpacity={0.1}/>
                    </linearGradient>
                  );
                })}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="name"
                tickFormatter={formatLabel}
                angle={-45}
                textAnchor="end"
                height={80}
                tick={{ fontSize: 10, fill: '#64748B' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#475569' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  padding: '12px'
                }}
                labelStyle={{ 
                  fontWeight: 600, 
                  color: '#1E293B',
                  marginBottom: '8px',
                  fontSize: '13px'
                }}
                itemStyle={{ 
                  color: '#475569',
                  fontSize: '12px',
                  padding: '4px 0'
                }}
                labelFormatter={(label) => `📅 ${formatLabel(label)}`}
                formatter={formatTooltipValue}
                cursor={{ stroke: '#0EA5E9', strokeWidth: 1, strokeDasharray: '3 3' }}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}
                iconType="line"
                onClick={(e) => handleLegendClick(e.dataKey as string)}
                style={{ cursor: 'pointer' }}
              />
              <Brush 
                dataKey="name" 
                height={30}
                stroke="#0EA5E9"
                fill="#E0F2FE"
              />
              {datasets.map((dataset, index) => {
                const dataKey = dataset.label || `Series ${index + 1}`;
                if (!activeSeries.has(dataKey)) return null;
                
                const label = (dataset.label || '').toLowerCase().trim();
                let color = MEDICAL_COLORS[label] || 
                           dataset.borderColor || 
                           dataset.backgroundColor || 
                           PIE_COLORS[index % PIE_COLORS.length];
                
                return (
                  <Area
                    key={dataKey}
                    type="monotone"
                    dataKey={dataKey}
                    stroke={color}
                    strokeWidth={3}
                    fill={`url(#gradient-${index})`}
                    isAnimationActive
                    animationDuration={800}
                    animationBegin={index * 100}
                  />
                );
              })}
            </AreaChart>
          ) : isBarChart ? (
            <BarChart data={rechartsData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="name"
                tickFormatter={formatLabel}
                angle={-45}
                textAnchor="end"
                height={80}
                tick={{ fontSize: 10, fill: '#64748B' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#475569' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  padding: '12px'
                }}
                labelStyle={{ 
                  fontWeight: 600, 
                  color: '#1E293B',
                  marginBottom: '8px',
                  fontSize: '13px'
                }}
                itemStyle={{ 
                  color: '#475569',
                  fontSize: '12px',
                  padding: '4px 0'
                }}
                labelFormatter={(label) => `📅 ${formatLabel(label)}`}
                formatter={formatTooltipValue}
                cursor={{ fill: '#E0F2FE', opacity: 0.3 }}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}
                iconType="rect"
                onClick={(e) => handleLegendClick(e.dataKey as string)}
                style={{ cursor: 'pointer' }}
              />
              <Brush 
                dataKey="name" 
                height={30}
                stroke="#0EA5E9"
                fill="#E0F2FE"
              />
              {datasets.map((dataset, index) => {
                const dataKey = dataset.label || `Series ${index + 1}`;
                if (!activeSeries.has(dataKey)) return null;
                
                const label = (dataset.label || '').toLowerCase().trim();
                // Try to match medical colors first - check full label and key terms
                let color = MEDICAL_COLORS[label];
                if (!color) {
                  // Try matching key terms in the label
                  for (const [key, value] of Object.entries(MEDICAL_COLORS)) {
                    if (label.includes(key)) {
                      color = value;
                      break;
                    }
                  }
                }
                // Fallback to dataset color or palette
                color = color || 
                       dataset.backgroundColor || 
                       dataset.borderColor || 
                       PIE_COLORS[index % PIE_COLORS.length];
                
                return (
                  <Bar
                    key={dataKey}
                    dataKey={dataKey}
                    fill={color}
                    barSize={20}
                    radius={[6, 6, 0, 0]}
                    isAnimationActive
                    animationDuration={800}
                    animationBegin={index * 100}
                  />
                );
              })}
            </BarChart>
          ) : (
            <LineChart data={rechartsData} margin={{ top: 20, right: hasDualYAxis ? 80 : 30, left: 20, bottom: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="name"
                tickFormatter={formatLabel}
                angle={-45}
                textAnchor="end"
                height={60}
                tick={{ fontSize: 10, fill: '#64748B' }}
              />
              {/* Primary (left) Y-axis */}
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12, fill: '#475569' }}
                label={hasDualYAxis ? { value: dualYAxis!.left.label, angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#475569' } } : undefined}
              />
              {/* Secondary (right) Y-axis — only when dualYAxis is set */}
              {hasDualYAxis && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12, fill: '#475569' }}
                  label={{ value: dualYAxis!.right.label, angle: 90, position: 'insideRight', style: { fontSize: 11, fill: '#475569' } }}
                />
              )}
              {/* Clinical reference range lines (normal + critical boundaries) */}
              {referenceLines.map((ref: any, idx: number) => (
                <ReferenceLine
                  key={`ref-${idx}`}
                  y={ref.y}
                  yAxisId="left"
                  stroke={ref.color || '#22c55e'}
                  strokeDasharray={ref.dash || '5 5'}
                  strokeWidth={1.5}
                >
                  <Label
                    value={ref.label}
                    position="right"
                    fill={ref.color || '#22c55e'}
                    fontSize={10}
                    fontWeight={500}
                  />
                </ReferenceLine>
              ))}
              {/* Normal range shaded area (if we have both low and high normal lines) */}
              {referenceLines.filter((r: any) => r.label?.includes('Normal')).length >= 2 && (
                <ReferenceArea
                  y1={referenceLines.find((r: any) => r.label?.includes('Low Normal'))?.y}
                  y2={referenceLines.find((r: any) => r.label?.includes('High Normal'))?.y}
                  yAxisId="left"
                  fill="#22c55e"
                  fillOpacity={0.06}
                  strokeOpacity={0}
                />
              )}
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ stroke: '#0EA5E9', strokeWidth: 1, strokeDasharray: '3 3' }}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}
                iconType="line"
                onClick={(e) => handleLegendClick(e.dataKey as string)}
                style={{ cursor: 'pointer' }}
              />
              <Brush 
                dataKey="name" 
                height={30}
                stroke="#0EA5E9"
                fill="#E0F2FE"
              />
              {datasets.map((dataset, index) => {
                const dataKey = dataset.label || `Series ${index + 1}`;
                if (!activeSeries.has(dataKey)) return null;
                
                const label = (dataset.label || '').toLowerCase().trim();
                // Try to match medical colors first - check full label and key terms
                let color = MEDICAL_COLORS[label];
                if (!color) {
                  // Try matching key terms in the label
                  for (const [key, value] of Object.entries(MEDICAL_COLORS)) {
                    if (label.includes(key)) {
                      color = value;
                      break;
                    }
                  }
                }
                // Fallback to dataset color or palette
                color = color || 
                       dataset.borderColor || 
                       dataset.backgroundColor || 
                       PIE_COLORS[index % PIE_COLORS.length];
                
                return (
                  <Line
                    key={dataKey}
                    type="monotone"
                    dataKey={dataKey}
                    stroke={color}
                    strokeWidth={3}
                    dot={{ fill: color, r: 4, strokeWidth: 2, stroke: '#fff' }}
                    activeDot={{ r: 6, stroke: color, strokeWidth: 2, fill: '#fff' }}
                    yAxisId={(dataset as any).yAxisID || 'left'}
                    isAnimationActive
                    animationDuration={800}
                    animationBegin={index * 100}
                    connectNulls={false}
                  />
                );
              })}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </PremiumChartCard>
  );
}

