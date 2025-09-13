'use client';

import React from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, ExternalLink, DollarSign } from 'lucide-react';
import { CostPoint } from '@/lib/costs/types';

interface BudgetBannerProps {
  currentCosts: CostPoint[];
  budgets?: Array<{
    name: string;
    amount: number;
    unit: string;
    threshold?: number; // Percentage threshold (e.g., 80 for 80%)
    link?: string; // Link to AWS Budgets console
  }>;
  loading?: boolean;
}

export function BudgetBanner({ currentCosts, budgets = [], loading = false }: BudgetBannerProps) {
  // Calculate current month total
  const currentTotal = React.useMemo(() => {
    if (!currentCosts || currentCosts.length === 0) return 0;
    
    // Get the latest month's cost
    const sortedCosts = [...currentCosts].sort((a, b) => 
      new Date(b.date).getTime() - new Date(a.date).getTime()
    );
    
    return sortedCosts[0]?.amount || 0;
  }, [currentCosts]);

  // Don't show banner if no budgets are configured or loading
  if (loading || budgets.length === 0) {
    return null;
  }

  // Format currency
  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Check budget status for each budget
  const budgetStatuses = budgets.map(budget => {
    const percentage = budget.amount > 0 ? (currentTotal / budget.amount) * 100 : 0;
    const threshold = budget.threshold || 80; // Default to 80% threshold
    
    let status: 'under' | 'warning' | 'over';
    if (percentage >= 100) {
      status = 'over';
    } else if (percentage >= threshold) {
      status = 'warning';
    } else {
      status = 'under';
    }
    
    return {
      ...budget,
      currentSpend: currentTotal,
      percentage,
      status,
    };
  });

  // Find the most critical budget status
  const criticalBudget = budgetStatuses.find(b => b.status === 'over') || 
                        budgetStatuses.find(b => b.status === 'warning') || 
                        budgetStatuses[0];

  if (!criticalBudget) return null;

  // Determine alert styling based on status
  const getAlertProps = (status: string) => {
    switch (status) {
      case 'over':
        return {
          className: 'border-red-200 bg-red-50',
          icon: AlertTriangle,
          iconColor: 'text-red-600',
          textColor: 'text-red-800',
        };
      case 'warning':
        return {
          className: 'border-yellow-200 bg-yellow-50',
          icon: AlertTriangle,
          iconColor: 'text-yellow-600',
          textColor: 'text-yellow-800',
        };
      default:
        return {
          className: 'border-green-200 bg-green-50',
          icon: CheckCircle,
          iconColor: 'text-green-600',
          textColor: 'text-green-800',
        };
    }
  };

  const alertProps = getAlertProps(criticalBudget.status);
  const AlertIcon = alertProps.icon;

  // Get status message
  const getStatusMessage = () => {
    const remaining = criticalBudget.amount - criticalBudget.currentSpend;
    
    switch (criticalBudget.status) {
      case 'over':
        return `Budget exceeded by ${formatCurrency(Math.abs(remaining), criticalBudget.unit)}`;
      case 'warning':
        return `${formatCurrency(remaining, criticalBudget.unit)} remaining (${(100 - criticalBudget.percentage).toFixed(1)}% of budget)`;
      default:
        return `${formatCurrency(remaining, criticalBudget.unit)} remaining (${criticalBudget.percentage.toFixed(1)}% used)`;
    }
  };

  return (
    <Alert className={alertProps.className}>
      <AlertIcon className={`h-4 w-4 ${alertProps.iconColor}`} />
      <AlertDescription>
        <div className="flex items-center justify-between">
          <div className={alertProps.textColor}>
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              <span className="font-medium">
                Budget: {criticalBudget.name}
              </span>
              <span className="text-sm">
                ({formatCurrency(criticalBudget.currentSpend, criticalBudget.unit)} / {formatCurrency(criticalBudget.amount, criticalBudget.unit)})
              </span>
            </div>
            <p className="text-sm mt-1">
              {getStatusMessage()}
            </p>
          </div>
          
          {criticalBudget.link && (
            <Button
              variant="outline"
              size="sm"
              asChild
              className={`ml-4 ${alertProps.textColor} border-current hover:bg-current hover:bg-opacity-10`}
            >
              <a href={criticalBudget.link} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-1" />
                View in AWS
              </a>
            </Button>
          )}
        </div>
        
        {budgetStatuses.length > 1 && (
          <div className="mt-2 text-sm">
            <details className="cursor-pointer">
              <summary className={`${alertProps.textColor} font-medium`}>
                View all budgets ({budgetStatuses.length})
              </summary>
              <div className="mt-2 space-y-1">
                {budgetStatuses.map((budget, index) => (
                  <div key={index} className="flex justify-between text-xs">
                    <span>{budget.name}:</span>
                    <span>
                      {formatCurrency(budget.currentSpend, budget.unit)} / {formatCurrency(budget.amount, budget.unit)}
                      ({budget.percentage.toFixed(1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}