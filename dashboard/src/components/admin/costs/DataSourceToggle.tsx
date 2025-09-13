import { useState } from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { InfoIcon } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export type DataSource = 'ce' | 'athena';

interface DataSourceToggleProps {
  dataSource: DataSource;
  onChange: (source: DataSource) => void;
  disabled?: boolean;
}

export function DataSourceToggle({
  dataSource,
  onChange,
  disabled,
}: DataSourceToggleProps) {
  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-2">
        <Label htmlFor="data-source-toggle" className="text-sm font-medium">
          Data Source
        </Label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <InfoIcon className="h-4 w-4 text-gray-400" />
            </TooltipTrigger>
            <TooltipContent className="max-w-sm">
              <p className="text-sm">
                <strong>Cost Explorer (CE):</strong> Real-time AWS cost data
                with ~24h delay. Better for recent activity and forecasting.
              </p>
              <p className="text-sm mt-2">
                <strong>Athena/CUR:</strong> Raw billing data with
                resource-level details. Better for detailed analysis and custom
                reporting.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <Badge
            variant={dataSource === 'ce' ? 'default' : 'secondary'}
            className="text-xs"
          >
            Cost Explorer
          </Badge>
          <Switch
            id="data-source-toggle"
            checked={dataSource === 'athena'}
            onCheckedChange={(checked) => onChange(checked ? 'athena' : 'ce')}
            disabled={disabled}
          />
          <Badge
            variant={dataSource === 'athena' ? 'default' : 'secondary'}
            className="text-xs"
          >
            Athena/CUR
          </Badge>
        </div>
      </div>

      {/* Data source indicator */}
      <div className="text-xs text-gray-500">
        {dataSource === 'ce' && (
          <span>Using Cost Explorer API • Updated daily</span>
        )}
        {dataSource === 'athena' && (
          <span>Using CUR data via Athena • Updated hourly</span>
        )}
      </div>
    </div>
  );
}
