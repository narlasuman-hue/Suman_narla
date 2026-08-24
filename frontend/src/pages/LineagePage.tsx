import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { FiGitBranch, FiArrowUp, FiArrowDown } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getFullLineage,
  getUpstreamLineage,
  getDownstreamLineage,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

const LineagePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [lineage, setLineage] = useState<any>(null);
  const [upstream, setUpstream] = useState<any[]>([]);
  const [downstream, setDownstream] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'full' | 'upstream' | 'downstream'>('full');

  useEffect(() => {
    const loadLineage = async () => {
      if (!id) return;

      try {
        setLoading(true);

        const [fullData, upstreamData, downstreamData] = await Promise.all([
          getFullLineage(parseInt(id)),
          getUpstreamLineage(parseInt(id)),
          getDownstreamLineage(parseInt(id)),
        ]);

        setLineage(fullData);
        setUpstream(upstreamData?.upstream?.[id] || []);
        setDownstream(downstreamData?.downstream?.[id] || []);
      } catch (error) {
        toast.error('Failed to load lineage data');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadLineage();
  }, [id]);

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <FiGitBranch className="text-purple-600" size={32} />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Data Lineage</h1>
          <p className="text-gray-600">Table ID: {id}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow border-b border-gray-200">
        <div className="flex">
          {['full', 'upstream', 'downstream'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`flex-1 px-6 py-4 font-medium text-center transition ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'full' && 'Full Lineage'}
              {tab === 'upstream' && 'Upstream (Sources)'}
              {tab === 'downstream' && 'Downstream (Targets)'}
            </button>
          ))}
        </div>
      </div>

      {/* Lineage Visualization */}
      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'full' && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex-1">
                <p className="text-sm text-gray-600">Central Table</p>
                <p className="text-lg font-bold text-gray-900">
                  {lineage?.table_name || 'Table'}
                </p>
              </div>
            </div>

            {/* Upstream in Full View */}
            {upstream.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <FiArrowUp className="text-orange-600" size={20} />
                  <h3 className="font-bold text-gray-900">Upstream Sources</h3>
                  <span className="bg-orange-100 text-orange-800 text-xs font-semibold px-2 py-1 rounded">
                    {upstream.length}
                  </span>
                </div>

                <div className="space-y-2 ml-4 border-l-2 border-orange-300">
                  {upstream.map((source: any, idx: number) => (
                    <div key={idx} className="pl-4 py-2 bg-orange-50 rounded">
                      <p className="font-medium text-gray-900">{source.source_name}</p>
                      <p className="text-sm text-gray-600">
                        {source.source_db} {source.job_id && `• Job: ${source.job_id}`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Downstream in Full View */}
            {downstream.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <FiArrowDown className="text-green-600" size={20} />
                  <h3 className="font-bold text-gray-900">Downstream Targets</h3>
                  <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                    {downstream.length}
                  </span>
                </div>

                <div className="space-y-2 ml-4 border-l-2 border-green-300">
                  {downstream.map((target: any, idx: number) => (
                    <div key={idx} className="pl-4 py-2 bg-green-50 rounded">
                      <p className="font-medium text-gray-900">{target.target_name}</p>
                      <p className="text-sm text-gray-600">
                        {target.target_db} {target.job_id && `• Job: ${target.job_id}`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {upstream.length === 0 && downstream.length === 0 && (
              <div className="text-center py-8 text-gray-600">
                <p>No lineage data available for this table</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'upstream' && (
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FiArrowUp className="text-orange-600" size={24} />
              Upstream Sources ({upstream.length})
            </h3>

            {upstream.length > 0 ? (
              <div className="space-y-3">
                {upstream.map((source: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-gray-900 text-lg">{source.source_name}</p>
                        <p className="text-sm text-gray-600 mt-1">
                          Database: <span className="font-medium">{source.source_db}</span>
                        </p>
                        {source.job_id && (
                          <p className="text-sm text-gray-600">
                            Job ID: <span className="font-medium">{source.job_id}</span>
                          </p>
                        )}
                      </div>
                      <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded text-sm font-medium">
                        Source
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-600">
                <p>No upstream sources found</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'downstream' && (
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FiArrowDown className="text-green-600" size={24} />
              Downstream Targets ({downstream.length})
            </h3>

            {downstream.length > 0 ? (
              <div className="space-y-3">
                {downstream.map((target: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-gray-900 text-lg">{target.target_name}</p>
                        <p className="text-sm text-gray-600 mt-1">
                          Database: <span className="font-medium">{target.target_db}</span>
                        </p>
                        {target.job_id && (
                          <p className="text-sm text-gray-600">
                            Job ID: <span className="font-medium">{target.job_id}</span>
                          </p>
                        )}
                      </div>
                      <span className="px-3 py-1 bg-green-100 text-green-800 rounded text-sm font-medium">
                        Target
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-600">
                <p>No downstream targets found</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Legend</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-orange-300 rounded"></div>
            <span className="text-gray-700">Upstream: Where data comes from</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-green-300 rounded"></div>
            <span className="text-gray-700">Downstream: Where data goes</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-blue-300 rounded"></div>
            <span className="text-gray-700">Central Table: The table being analyzed</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LineagePage;
