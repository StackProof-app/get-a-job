// profile-schema.ts — Typed profile schema for GAJ's ATS form autofill.
// Phase 10's Python adapter will parse profile.yaml from disk and rely on the
// required-field list established here.

export type WorkAuthStatus =
  | 'us_citizen'
  | 'permanent_resident'
  | 'visa_holder'
  | 'needs_sponsorship';

export type EmploymentStatus = 'employed' | 'unemployed' | 'freelance';

export type LocationPreference = 'remote' | 'hybrid' | 'onsite';

export type EeocGender =
  | 'male'
  | 'female'
  | 'non_binary'
  | 'decline_to_state';

export type EeocEthnicity =
  | 'white'
  | 'black_or_african_american'
  | 'hispanic_or_latino'
  | 'asian'
  | 'native_american'
  | 'pacific_islander'
  | 'two_or_more'
  | 'decline_to_state';

export type EeocVeteranStatus =
  | 'protected_veteran'
  | 'not_a_veteran'
  | 'decline_to_state';

export type EeocDisabilityStatus = 'yes' | 'no' | 'decline_to_state';

export interface ResumeVariant {
  key: string;
  label: string;
  path: string;
  use_when: string;
}

export interface Profile {
  identity: {
    full_name: string;
    preferred_name: string;
    pronouns?: string;
    email: string;
    phone: string;
    linkedin_url: string;
    github_url: string;
    portfolio_url: string;
  };
  address: {
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  work_auth: {
    status: WorkAuthStatus;
    sponsorship_required_now: boolean;
    sponsorship_required_future: boolean;
  };
  relocation: {
    willing_to_relocate: boolean;
    preferred_locations: string[];
    current_location_preference: LocationPreference;
  };
  employment: {
    current_status: EmploymentStatus;
    notice_period_days: number;
    earliest_start_date: string;
  };
  resume: {
    variants: ResumeVariant[];
  };
  eeoc_voluntary: {
    gender: EeocGender;
    ethnicity: EeocEthnicity;
    veteran_status: EeocVeteranStatus;
    disability_status: EeocDisabilityStatus;
  };
  target_roles: string[];
  employment_types: string[];
}

const WORK_AUTH_VALUES: ReadonlyArray<WorkAuthStatus> = [
  'us_citizen',
  'permanent_resident',
  'visa_holder',
  'needs_sponsorship',
];

const EMPLOYMENT_VALUES: ReadonlyArray<EmploymentStatus> = [
  'employed',
  'unemployed',
  'freelance',
];

export function defaultProfile(): Profile {
  const today = new Date();
  const plus14 = new Date(today.getTime() + 14 * 86400000);
  const iso = plus14.toISOString().slice(0, 10);
  return {
    identity: {
      full_name: '',
      preferred_name: '',
      email: '',
      phone: '',
      linkedin_url: '',
      github_url: '',
      portfolio_url: '',
    },
    address: {
      city: '',
      state: '',
      postal_code: '',
      country: 'US',
    },
    work_auth: {
      status: 'us_citizen',
      sponsorship_required_now: false,
      sponsorship_required_future: false,
    },
    relocation: {
      willing_to_relocate: false,
      preferred_locations: [],
      current_location_preference: 'remote',
    },
    employment: {
      current_status: 'employed',
      notice_period_days: 14,
      earliest_start_date: iso,
    },
    resume: {
      variants: [],
    },
    eeoc_voluntary: {
      gender: 'decline_to_state',
      ethnicity: 'decline_to_state',
      veteran_status: 'decline_to_state',
      disability_status: 'decline_to_state',
    },
    target_roles: [],
    employment_types: [],
  };
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null;
}

export function validateProfile(
  obj: unknown
): { ok: true; profile: Profile } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  if (!isObject(obj)) {
    return { ok: false, errors: ['root: not an object'] };
  }
  const p = obj as Record<string, unknown>;

  const identity = isObject(p.identity) ? p.identity : null;
  if (!identity) {
    errors.push('identity: missing');
  } else {
    if (typeof identity.full_name !== 'string' || identity.full_name.trim() === '') {
      errors.push('identity.full_name: missing');
    }
    if (typeof identity.email !== 'string' || identity.email.trim() === '') {
      errors.push('identity.email: missing');
    } else if (!identity.email.includes('@')) {
      errors.push('identity.email: invalid shape (no @)');
    }
    if (typeof identity.phone !== 'string' || identity.phone.trim() === '') {
      errors.push('identity.phone: missing');
    }
  }

  const workAuth = isObject(p.work_auth) ? p.work_auth : null;
  if (!workAuth) {
    errors.push('work_auth: missing');
  } else if (
    typeof workAuth.status !== 'string' ||
    !WORK_AUTH_VALUES.includes(workAuth.status as WorkAuthStatus)
  ) {
    errors.push(
      `work_auth.status: invalid enum value "${String(workAuth.status)}"`
    );
  }

  const address = isObject(p.address) ? p.address : null;
  if (!address) {
    errors.push('address: missing');
  } else if (typeof address.country !== 'string' || address.country.trim() === '') {
    errors.push('address.country: missing');
  }

  const resume = isObject(p.resume) ? p.resume : null;
  if (!resume) {
    errors.push('resume: missing');
  } else if (!Array.isArray(resume.variants) || resume.variants.length === 0) {
    errors.push('resume.variants: must contain at least one variant');
  }

  const employment = isObject(p.employment) ? p.employment : null;
  if (employment) {
    if (
      typeof employment.current_status !== 'string' ||
      !EMPLOYMENT_VALUES.includes(employment.current_status as EmploymentStatus)
    ) {
      errors.push(
        `employment.current_status: invalid enum value "${String(employment.current_status)}"`
      );
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return { ok: true, profile: obj as unknown as Profile };
}
