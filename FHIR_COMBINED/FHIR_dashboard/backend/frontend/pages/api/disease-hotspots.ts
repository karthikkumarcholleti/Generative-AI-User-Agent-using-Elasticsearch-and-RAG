import { NextApiRequest, NextApiResponse } from 'next';
import fs from 'fs';
import path from 'path';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    // Get dataset parameter (default to 'real')
    const { dataset = 'real' } = req.query;
    
    // Determine which data file to load
    let dataPath: string;
    let dataSource: string;
    
    if (dataset === 'synthea' || dataset === 'test') {
      dataPath = path.join(process.cwd(), '../disease_hotspot_detection/results/communicable_test/disease_hotspots.csv');
      dataSource = 'Synthea Test Data (Communicable Diseases)';
    } else {
      dataPath = path.join(process.cwd(), '../disease_hotspot_detection/results/disease_hotspots.csv');
      dataSource = 'Real FHIR Data';
    }
    
    if (!fs.existsSync(dataPath)) {
      return res.status(404).json({ error: 'Hotspot data not found', path: dataPath });
    }

    const csvData = fs.readFileSync(dataPath, 'utf-8');
    const lines = csvData.split('\n');
    const headers = lines[0].split(',');
    
    // Parse CSV data
    const hotspots = lines.slice(1)
      .filter(line => line.trim())
      .map(line => {
        const values = line.split(',');
        const hotspot: any = {};
        headers.forEach((header, index) => {
          const key = header.trim();
          const value = values[index]?.trim();
          
          // Convert numeric fields
          if (['total_cases', 'latitude', 'longitude', 'cluster_id', 'growth_rate', 'mean_age'].includes(key)) {
            hotspot[key] = parseFloat(value) || 0;
          } else if (['is_hotspot'].includes(key)) {
            hotspot[key] = value === 'True';
          } else {
            hotspot[key] = value;
          }
        });
        return hotspot;
      });

    // Calculate statistics
    const stats = {
      totalCommunities: new Set(hotspots.map(h => h.patient_city)).size,
      totalDiseases: new Set(hotspots.map(h => h.disease_category)).size,
      totalHotspots: hotspots.filter(h => h.is_hotspot).length,
      totalCases: hotspots.reduce((sum, h) => sum + h.total_cases, 0)
    };

    // Get unique diseases
    const diseases = Array.from(new Set(hotspots.map(h => h.disease_category)))
      .map(code => {
        const diseaseData = hotspots.find(h => h.disease_category === code);
        return {
          code,
          name: diseaseData?.disease_name || code,
          totalCases: hotspots.filter(h => h.disease_category === code).reduce((sum, h) => sum + h.total_cases, 0),
          hotspots: hotspots.filter(h => h.disease_category === code && h.is_hotspot).length
        };
      })
      .sort((a, b) => b.totalCases - a.totalCases);

    // Calculate model performance metrics
    const totalRecords = hotspots.length;
    const totalHotspots = hotspots.filter(h => h.is_hotspot).length;
    const hotspotsRate = totalRecords > 0 ? (totalHotspots / totalRecords * 100) : 0;
    const totalClusters = new Set(hotspots.filter(h => h.cluster_id !== -1).map(h => h.cluster_id)).size;
    const avgClusterSize = totalClusters > 0 ? totalHotspots / totalClusters : 0;

    const modelPerformance = {
      totalRecords,
      hotspotsDetected: totalHotspots,
      detectionRate: parseFloat(hotspotsRate.toFixed(1)),
      clustersFound: totalClusters,
      avgClusterSize: parseFloat(avgClusterSize.toFixed(1)),
      dataSource,
      modelAlgorithm: 'DBSCAN',
      modelParameters: { eps: 0.3, min_samples: 3 },
      isTestData: dataset === 'synthea' || dataset === 'test'
    };

    res.status(200).json({
      hotspots: hotspots.map(h => ({
        id: `${h.patient_city}-${h.disease_category}`,
        city: h.patient_city,
        state: h.patient_state || 'MI',
        latitude: h.latitude,
        longitude: h.longitude,
        disease: h.disease_category,
        diseaseName: h.disease_name,
        totalCases: h.total_cases,
        isHotspot: h.is_hotspot,
        clusterId: h.cluster_id,
        growthRate: h.growth_rate,
        meanAge: h.mean_age,
        malePercentage: h.male_percentage,
        ageRange: h.age_range
      })),
      stats,
      diseases,
      modelPerformance,
      lastUpdated: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error reading hotspot data:', error);
    res.status(500).json({ error: 'Failed to load hotspot data' });
  }
}
