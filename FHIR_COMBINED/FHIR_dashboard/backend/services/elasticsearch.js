// backend/services/elasticsearch.js
const { Client } = require('@elastic/elasticsearch');

class ElasticSearchService {
  constructor() {
    this.client = null;
    this.esUrl = process.env.ELASTICSEARCH_URL || 'https://localhost:9200';
    this.esUsername = process.env.ELASTICSEARCH_USERNAME || 'elastic';
    this.esPassword = process.env.ELASTICSEARCH_PASSWORD || 'P@ssw0rd';
    this.indexName = process.env.ELASTICSEARCH_INDEX || 'patient_data';
    
    this.connect();
  }

  connect() {
    try {
      this.client = new Client({
        node: this.esUrl,
        auth: {
          username: this.esUsername,
          password: this.esPassword
        },
        tls: {
          rejectUnauthorized: false
        }
      });
      
      // Test connection
      this.client.ping()
        .then(() => {
          console.log('✅ Connected to ElasticSearch at', this.esUrl);
        })
        .catch((err) => {
          console.error('❌ ElasticSearch connection failed:', err.message);
          this.client = null;
        });
    } catch (error) {
      console.error('❌ Failed to initialize ElasticSearch client:', error.message);
      this.client = null;
    }
  }

  isConnected() {
    if (!this.client) return false;
    try {
      return this.client.ping().then(() => true).catch(() => false);
    } catch {
      return false;
    }
  }

  // Search patients with autocomplete
  async searchPatients(query, limit = 20) {
    if (!this.client) {
      throw new Error('ElasticSearch not connected');
    }

    try {
      const searchBody = {
        query: {
          bool: {
            must: [
              { term: { data_type: 'demographics' } }
            ],
            should: [
              {
                multi_match: {
                  query: query,
                  fields: [
                    'patient_name^2.0',
                    'patient_id^1.5',
                    'content^1.0'
                  ],
                  type: 'best_fields',
                  fuzziness: 'AUTO'
                }
              },
              {
                wildcard: {
                  patient_name: `*${query.toLowerCase()}*`
                }
              },
              {
                prefix: {
                  patient_id: query
                }
              }
            ],
            minimum_should_match: 1
          }
        },
        size: limit,
        collapse: {
          field: 'patient_id'
        },
        sort: [
          { _score: { order: 'desc' } },
          { timestamp: { order: 'desc' } }
        ]
      };

      const response = await this.client.search({
        index: this.indexName,
        body: searchBody
      });

      // Extract unique patients
      const patientsMap = new Map();
      response.body.hits.hits.forEach(hit => {
        const patientId = hit._source.patient_id;
        if (!patientsMap.has(patientId)) {
          patientsMap.set(patientId, {
            patient_id: patientId,
            name: hit._source.patient_name || `Patient ${patientId}`,
            metadata: hit._source.metadata || {},
            score: hit._score
          });
        }
      });

      return Array.from(patientsMap.values());
    } catch (error) {
      console.error('Error searching patients:', error);
      throw error;
    }
  }

  // Search observations
  async searchObservations(patientId, query, filters = {}) {
    if (!this.client) {
      throw new Error('ElasticSearch not connected');
    }

    try {
      const searchBody = {
        query: {
          bool: {
            must: [
              { term: { patient_id: patientId } },
              { term: { data_type: 'observations' } }
            ],
            should: [
              {
                multi_match: {
                  query: query,
                  fields: [
                    'metadata.display^2.0',
                    'metadata.value^1.5',
                    'content^1.0'
                  ],
                  type: 'best_fields',
                  fuzziness: 'AUTO'
                }
              }
            ],
            minimum_should_match: query ? 1 : 0
          }
        },
        size: 100,
        sort: [{ timestamp: { order: 'desc' } }]
      };

      // Add filters
      if (filters.dateFrom || filters.dateTo) {
        searchBody.query.bool.filter = [{
          range: {
            timestamp: {
              gte: filters.dateFrom,
              lte: filters.dateTo
            }
          }
        }];
      }

      if (filters.observationType) {
        if (!searchBody.query.bool.filter) {
          searchBody.query.bool.filter = [];
        }
        searchBody.query.bool.filter.push({
          wildcard: {
            'metadata.display': `*${filters.observationType}*`
          }
        });
      }

      const response = await this.client.search({
        index: this.indexName,
        body: searchBody
      });

      return response.body.hits.hits.map(hit => ({
        ...hit._source,
        score: hit._score
      }));
    } catch (error) {
      console.error('Error searching observations:', error);
      throw error;
    }
  }

  // Search conditions
  async searchConditions(patientId, query, filters = {}) {
    if (!this.client) {
      throw new Error('ElasticSearch not connected');
    }

    try {
      const searchBody = {
        query: {
          bool: {
            must: [
              { term: { patient_id: patientId } },
              { term: { data_type: 'conditions' } }
            ],
            should: [
              {
                multi_match: {
                  query: query,
                  fields: [
                    'metadata.display^2.0',
                    'content^1.0'
                  ],
                  type: 'best_fields',
                  fuzziness: 'AUTO'
                }
              }
            ],
            minimum_should_match: query ? 1 : 0
          }
        },
        size: 100,
        sort: [{ timestamp: { order: 'desc' } }]
      };

      // Add filters
      if (filters.status) {
        if (!searchBody.query.bool.filter) {
          searchBody.query.bool.filter = [];
        }
        searchBody.query.bool.filter.push({
          term: { 'metadata.status': filters.status }
        });
      }

      const response = await this.client.search({
        index: this.indexName,
        body: searchBody
      });

      return response.body.hits.hits.map(hit => ({
        ...hit._source,
        score: hit._score
      }));
    } catch (error) {
      console.error('Error searching conditions:', error);
      throw error;
    }
  }

  // Search clinical notes
  async searchNotes(patientId, query, filters = {}) {
    if (!this.client) {
      throw new Error('ElasticSearch not connected');
    }

    try {
      const searchBody = {
        query: {
          bool: {
            must: [
              { term: { data_type: 'notes' } }
            ],
            should: [
              {
                multi_match: {
                  query: query,
                  fields: [
                    'content^2.0',
                    'metadata.source_type^1.0'
                  ],
                  type: 'best_fields',
                  fuzziness: 'AUTO'
                }
              }
            ],
            minimum_should_match: query ? 1 : 0
          }
        },
        size: 50,
        sort: [{ timestamp: { order: 'desc' } }]
      };

      // Add patient filter if specified
      if (patientId) {
        searchBody.query.bool.must.push({ term: { patient_id: patientId } });
      }

      // Add date range filter
      if (filters.dateFrom || filters.dateTo) {
        if (!searchBody.query.bool.filter) {
          searchBody.query.bool.filter = [];
        }
        searchBody.query.bool.filter.push({
          range: {
            timestamp: {
              gte: filters.dateFrom,
              lte: filters.dateTo
            }
          }
        });
      }

      const response = await this.client.search({
        index: this.indexName,
        body: searchBody
      });

      return response.body.hits.hits.map(hit => ({
        ...hit._source,
        score: hit._score
      }));
    } catch (error) {
      console.error('Error searching notes:', error);
      throw error;
    }
  }

  // Get patient statistics using aggregations
  async getPatientStatistics(patientId) {
    if (!this.client) {
      throw new Error('ElasticSearch not connected');
    }

    try {
      const searchBody = {
        query: {
          term: { patient_id: patientId }
        },
        aggs: {
          by_data_type: {
            terms: {
              field: 'data_type',
              size: 10
            }
          },
          recent_observations: {
            filter: {
              term: { data_type: 'observations' }
            },
            aggs: {
              by_date: {
                date_histogram: {
                  field: 'timestamp',
                  calendar_interval: 'day',
                  order: { _key: 'desc' },
                  size: 30
                }
              }
            }
          }
        },
        size: 0
      };

      const response = await this.client.search({
        index: this.indexName,
        body: searchBody
      });

      return {
        total_documents: response.body.hits.total.value,
        data_types: response.body.aggregations.by_data_type.buckets.reduce((acc, bucket) => {
          acc[bucket.key] = bucket.doc_count;
          return acc;
        }, {}),
        recent_observations: response.body.aggregations.recent_observations.by_date.buckets
      };
    } catch (error) {
      console.error('Error getting patient statistics:', error);
      throw error;
    }
  }
}

// Export singleton instance
const elasticsearchService = new ElasticSearchService();
module.exports = elasticsearchService;

