import React from 'react';
import clsx from 'clsx';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color?: 'blue' | 'green' | 'purple' | 'indigo' | 'red' | 'orange';
}

const colorMap = {
  blue: 'bg-blue-50 text-blue-700',
  green: 'bg-green-50 text-green-700',
  purple: 'bg-purple-50 text-purple-700',
  indigo: 'bg-blue-50 text-blue-700',
  red: 'bg-red-50 text-red-700',
  orange: 'bg-orange-50 text-orange-700',
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  color = 'blue',
}) => {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg bg-white p-4 shadow">
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-600">{title}</p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">{value.toLocaleString()}</p>
      </div>
      <div className={clsx('rounded-lg p-2', colorMap[color])}>
        <Icon size={18} />
      </div>
    </div>
  );
};
