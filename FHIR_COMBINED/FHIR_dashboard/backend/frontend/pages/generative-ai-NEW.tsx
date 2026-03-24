// This is a TEMPORARY file to show the new structure
// Will be merged into generative-ai.tsx after review

// Section navigation items (matching SUMMARY_CATEGORIES but for sidebar)
const SECTION_NAV_ITEMS: Array<{
  id: SectionType;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}> = [
  { id: 'patients', label: 'Patients', icon: Users },
  { id: 'demographics', label: 'Demographics', icon: ClipboardList },
  { id: 'observations', label: 'Observations', icon: Activity },
  { id: 'conditions', label: 'Conditions', icon: Stethoscope },
  { id: 'notes', label: 'Notes', icon: BookOpenCheck },
  { id: 'care_plans', label: 'Care Plans', icon: Brain },
  { id: 'chat', label: 'AI Chat Interface', icon: Bot },
];

// Helper to get section label
const getSectionLabel = (section: SectionType): string => {
  return SECTION_NAV_ITEMS.find(item => item.id === section)?.label || section;
};

// Helper to get breadcrumb path
const getBreadcrumbPath = (): string[] => {
  if (!selectedPatient) return [];
  const sectionLabel = getSectionLabel(activeSection);
  return [selectedPatient.displayName, sectionLabel];
};

