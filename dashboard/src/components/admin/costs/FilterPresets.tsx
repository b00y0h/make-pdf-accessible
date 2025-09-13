'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Bookmark,
  BookmarkPlus,
  Trash2,
  Share2,
  Check,
  ChevronDown,
} from 'lucide-react';
import { CostFilters } from '@/lib/costs/types';
import { toast } from 'sonner';

interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  filters: CostFilters;
  createdAt: string;
  isDefault?: boolean;
}

interface FilterPresetsProps {
  currentFilters: CostFilters;
  onApplyPreset: (filters: CostFilters) => void;
  onShare?: (url: string) => void;
}

const DEFAULT_PRESETS: FilterPreset[] = [
  {
    id: 'monthly-overview',
    name: 'Monthly Overview',
    description: 'Last 12 months, all services, monthly view',
    filters: {
      dateRange: { preset: '12months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: [],
      accounts: [],
      regions: [],
      tags: {},
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
  {
    id: 'quarterly-analysis',
    name: 'Quarterly Analysis',
    description: 'Last 18 months for quarterly comparisons',
    filters: {
      dateRange: { preset: '18months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: [],
      accounts: [],
      regions: [],
      tags: {},
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
  {
    id: 'recent-trends',
    name: 'Recent Trends',
    description: 'Last 3 months with daily granularity',
    filters: {
      dateRange: { preset: '3months' },
      metric: 'UnblendedCost',
      granularity: 'DAILY',
      services: [],
      accounts: [],
      regions: [],
      tags: {},
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
  {
    id: 'compute-costs',
    name: 'Compute Services',
    description: 'Focus on EC2, Lambda, and ECS costs',
    filters: {
      dateRange: { preset: '12months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: ['AmazonEC2', 'AWSLambda', 'AmazonECS'],
      accounts: [],
      regions: [],
      tags: {},
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
  {
    id: 'storage-costs',
    name: 'Storage Services',
    description: 'S3, EBS, and other storage costs',
    filters: {
      dateRange: { preset: '12months' },
      metric: 'UnblendedCost',
      granularity: 'MONTHLY',
      services: ['AmazonS3', 'AmazonEBS', 'AmazonEFS'],
      accounts: [],
      regions: [],
      tags: {},
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
];

export function FilterPresets({
  currentFilters,
  onApplyPreset,
  onShare,
}: FilterPresetsProps) {
  const [presets, setPresets] = useState<FilterPreset[]>(DEFAULT_PRESETS);
  const [open, setOpen] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetDescription, setNewPresetDescription] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Load saved presets from localStorage
  useEffect(() => {
    const savedPresets = localStorage.getItem('cost-filter-presets');
    if (savedPresets) {
      try {
        const parsed = JSON.parse(savedPresets);
        setPresets([...DEFAULT_PRESETS, ...parsed]);
      } catch (error) {
        console.warn('Failed to load saved presets:', error);
      }
    }
  }, []);

  // Save presets to localStorage
  const savePresetsToStorage = (presets: FilterPreset[]) => {
    const customPresets = presets.filter((p) => !p.isDefault);
    localStorage.setItem('cost-filter-presets', JSON.stringify(customPresets));
  };

  // Save current filters as a new preset
  const saveCurrentAsPreset = () => {
    if (!newPresetName.trim()) {
      toast.error('Please enter a preset name');
      return;
    }

    const newPreset: FilterPreset = {
      id: `custom-${Date.now()}`,
      name: newPresetName.trim(),
      description: newPresetDescription.trim() || undefined,
      filters: { ...currentFilters },
      createdAt: new Date().toISOString(),
    };

    const updatedPresets = [...presets, newPreset];
    setPresets(updatedPresets);
    savePresetsToStorage(updatedPresets);

    setNewPresetName('');
    setNewPresetDescription('');
    setShowSaveDialog(false);

    toast.success(`Preset "${newPreset.name}" saved`);
  };

  // Delete a custom preset
  const deletePreset = (presetId: string) => {
    const updatedPresets = presets.filter((p) => p.id !== presetId);
    setPresets(updatedPresets);
    savePresetsToStorage(updatedPresets);

    toast.success('Preset deleted');
  };

  // Apply a preset
  const applyPreset = (preset: FilterPreset) => {
    onApplyPreset(preset.filters);
    setOpen(false);
    toast.success(`Applied preset: ${preset.name}`);
  };

  // Share current filters
  const shareCurrentFilters = () => {
    if (onShare) {
      // Generate shareable URL (this would come from the persistence hook)
      const baseUrl = window.location.origin + window.location.pathname;
      onShare(baseUrl);
    }
  };

  // Check if current filters match a preset
  const findMatchingPreset = () => {
    return presets.find((preset) => {
      return JSON.stringify(preset.filters) === JSON.stringify(currentFilters);
    });
  };

  const matchingPreset = findMatchingPreset();

  return (
    <div className="flex items-center gap-2">
      {/* Preset Selector */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2 min-w-[120px]"
          >
            <Bookmark className="h-4 w-4" />
            {matchingPreset ? matchingPreset.name : 'Presets'}
            <ChevronDown className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[350px] p-0">
          <Command>
            <CommandInput placeholder="Search presets..." />
            <CommandList>
              <CommandEmpty>No presets found.</CommandEmpty>

              {/* Default Presets */}
              <CommandGroup heading="Default Presets">
                {DEFAULT_PRESETS.map((preset) => (
                  <CommandItem
                    key={preset.id}
                    onSelect={() => applyPreset(preset)}
                    className="flex items-center justify-between cursor-pointer"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{preset.name}</span>
                        {matchingPreset?.id === preset.id && (
                          <Check className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      {preset.description && (
                        <p className="text-xs text-gray-600 mt-1">
                          {preset.description}
                        </p>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>

              {/* Custom Presets */}
              {presets.some((p) => !p.isDefault) && (
                <>
                  <CommandSeparator />
                  <CommandGroup heading="Custom Presets">
                    {presets
                      .filter((p) => !p.isDefault)
                      .map((preset) => (
                        <CommandItem
                          key={preset.id}
                          className="flex items-center justify-between cursor-pointer"
                        >
                          <div
                            className="flex-1"
                            onClick={() => applyPreset(preset)}
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{preset.name}</span>
                              {matchingPreset?.id === preset.id && (
                                <Check className="h-4 w-4 text-green-600" />
                              )}
                            </div>
                            {preset.description && (
                              <p className="text-xs text-gray-600 mt-1">
                                {preset.description}
                              </p>
                            )}
                          </div>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-red-100"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <Trash2 className="h-3 w-3 text-red-600" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>
                                  Delete Preset
                                </AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete &quot;
                                  {preset.name}&quot;? This action cannot be
                                  undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => deletePreset(preset.id)}
                                  className="bg-red-600 hover:bg-red-700"
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </CommandItem>
                      ))}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Save Current as Preset */}
      <AlertDialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <AlertDialogTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <BookmarkPlus className="h-4 w-4" />
            Save
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Save Filter Preset</AlertDialogTitle>
            <AlertDialogDescription>
              Save your current filter configuration for easy reuse.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Preset Name *</label>
              <Input
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                placeholder="e.g., Production Environment Costs"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">
                Description (optional)
              </label>
              <Input
                value={newPresetDescription}
                onChange={(e) => setNewPresetDescription(e.target.value)}
                placeholder="Brief description of this filter configuration"
                className="mt-1"
              />
            </div>

            {/* Preview of current filters */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Current Filters:</label>
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="secondary">
                  {currentFilters.dateRange.preset === 'custom'
                    ? `${currentFilters.dateRange.custom?.start} to ${currentFilters.dateRange.custom?.end}`
                    : currentFilters.dateRange.preset}
                </Badge>
                <Badge variant="secondary">
                  {currentFilters.metric} • {currentFilters.granularity}
                </Badge>
                {currentFilters.services &&
                  currentFilters.services.length > 0 && (
                    <Badge variant="secondary">
                      {currentFilters.services.length} service(s)
                    </Badge>
                  )}
                {currentFilters.accounts &&
                  currentFilters.accounts.length > 0 && (
                    <Badge variant="secondary">
                      {currentFilters.accounts.length} account(s)
                    </Badge>
                  )}
                {currentFilters.regions &&
                  currentFilters.regions.length > 0 && (
                    <Badge variant="secondary">
                      {currentFilters.regions.length} region(s)
                    </Badge>
                  )}
                {Object.keys(currentFilters.tags || {}).length > 0 && (
                  <Badge variant="secondary">
                    {Object.keys(currentFilters.tags || {}).length} tag
                    filter(s)
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={saveCurrentAsPreset}>
              Save Preset
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Share Button */}
      {onShare && (
        <Button
          variant="outline"
          size="sm"
          onClick={shareCurrentFilters}
          className="flex items-center gap-2"
        >
          <Share2 className="h-4 w-4" />
          Share
        </Button>
      )}
    </div>
  );
}
