export type FirewallEndpoint = {
  ip: string;
  username: string;
  password: string;
  ssh_port: number;
};

export type DeviceInfo = {
  vendor: string;
  model: string;
  os_version: string;
  raw_output?: string;
};

export type CompatibilityIssue = {
  category: string;
  severity: string;
  message: string;
};

export type Compatibility = {
  compatible: boolean;
  score: number;
  mode: string;
  issues: CompatibilityIssue[];
  conversion_matrix: Record<string, string>;
};

export type JobStatus = {
  job_id: string;
  status: string;
  progress: number;
  logs: string[];
  report_id?: string;
  source_device?: DeviceInfo;
  destination_device?: DeviceInfo;
  compatibility?: Compatibility;
};
