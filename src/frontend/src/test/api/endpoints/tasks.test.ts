import { describe, it, expect, beforeEach, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const client = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  return { client };
});

vi.mock('@/api/client', () => ({
  __esModule: true,
  default: mocks.client,
  tenantClient: mocks.client,
  // `taskPhotoUri` reads the active slug to rebuild an attachment URI from a
  // stored id, so the double has to answer it (#1339 review).
  getActiveTenantSlug: () => 'mein-garten',
}));

import * as tasks from '@/api/endpoints/tasks';

const client = mocks.client;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('tasks endpoints — workflow templates', () => {
  it('listWorkflows uses default pagination params', async () => {
    client.get.mockResolvedValue({ data: [] });
    await expect(tasks.listWorkflows()).resolves.toEqual([]);
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows', {
      params: { offset: 0, limit: 50 },
    });
  });

  it('listWorkflows adds species and target filters when provided', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listWorkflows(10, 5, 'sp1', 'plant' as never);
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows', {
      params: { offset: 10, limit: 5, species_key: 'sp1', target_entity_type: 'plant' },
    });
  });

  it('createWorkflow posts payload to /tasks/workflows', async () => {
    const wf = { key: 'w1' };
    client.post.mockResolvedValue({ data: wf });
    const payload = { name: 'WF' } as never;
    await expect(tasks.createWorkflow(payload)).resolves.toEqual(wf);
    expect(client.post).toHaveBeenCalledWith('/tasks/workflows', payload);
  });

  it('getWorkflow gets workflow by key', async () => {
    client.get.mockResolvedValue({ data: { key: 'w1' } });
    await tasks.getWorkflow('w1');
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows/w1');
  });

  it('updateWorkflow puts payload to workflow key', async () => {
    client.put.mockResolvedValue({ data: { key: 'w1' } });
    const payload = { name: 'X' } as never;
    await tasks.updateWorkflow('w1', payload);
    expect(client.put).toHaveBeenCalledWith('/tasks/workflows/w1', payload);
  });

  it('deleteWorkflow deletes workflow by key', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tasks.deleteWorkflow('w1');
    expect(client.delete).toHaveBeenCalledWith('/tasks/workflows/w1');
  });

  it('duplicateWorkflow posts with name param', async () => {
    client.post.mockResolvedValue({ data: { key: 'w2' } });
    await tasks.duplicateWorkflow('w1', 'Copy');
    expect(client.post).toHaveBeenCalledWith('/tasks/workflows/w1/duplicate', null, {
      params: { name: 'Copy' },
    });
  });

  it('listWorkflowExecutions gets executions for workflow', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listWorkflowExecutions('w1');
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows/w1/executions');
  });

  it('instantiateWorkflow posts instantiate request', async () => {
    client.post.mockResolvedValue({ data: { key: 'e1' } });
    const payload = { entity_key: 'p1' } as never;
    await tasks.instantiateWorkflow('w1', payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/workflows/w1/instantiate', payload);
  });
});

describe('tasks endpoints — workflow phases', () => {
  it('listWorkflowPhases gets phases for workflow', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listWorkflowPhases('w1');
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows/w1/phases');
  });

  it('createWorkflowPhase posts phase', async () => {
    client.post.mockResolvedValue({ data: { key: 'ph1' } });
    const payload = { name: 'Veg' } as never;
    await tasks.createWorkflowPhase('w1', payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/workflows/w1/phases', payload);
  });

  it('updateWorkflowPhase puts to /tasks/phases/{key}', async () => {
    client.put.mockResolvedValue({ data: { key: 'ph1' } });
    const payload = { name: 'X' } as never;
    await tasks.updateWorkflowPhase('ph1', payload);
    expect(client.put).toHaveBeenCalledWith('/tasks/phases/ph1', payload);
  });

  it('deleteWorkflowPhase deletes /tasks/phases/{key}', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tasks.deleteWorkflowPhase('ph1');
    expect(client.delete).toHaveBeenCalledWith('/tasks/phases/ph1');
  });

  it('reorderPhases puts phases array to reorder endpoint', async () => {
    client.put.mockResolvedValue({ data: [] });
    const phases = [{ key: 'ph1', phase_order: 0 }];
    await tasks.reorderPhases(phases);
    expect(client.put).toHaveBeenCalledWith('/tasks/phases/reorder', { phases });
  });

  it('listPhaseSuggestions gets phase suggestions', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listPhaseSuggestions();
    expect(client.get).toHaveBeenCalledWith('/tasks/phases/suggestions');
  });
});

describe('tasks endpoints — task templates', () => {
  it('listTaskTemplates gets templates for workflow', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listTaskTemplates('w1');
    expect(client.get).toHaveBeenCalledWith('/tasks/workflows/w1/templates');
  });

  it('createTaskTemplate posts to /tasks/templates', async () => {
    client.post.mockResolvedValue({ data: { key: 't1' } });
    const payload = { name: 'T' } as never;
    await tasks.createTaskTemplate(payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/templates', payload);
  });

  it('getTaskTemplate gets template by key', async () => {
    client.get.mockResolvedValue({ data: { key: 't1' } });
    await tasks.getTaskTemplate('t1');
    expect(client.get).toHaveBeenCalledWith('/tasks/templates/t1');
  });

  it('updateTaskTemplate puts template by key', async () => {
    client.put.mockResolvedValue({ data: { key: 't1' } });
    const payload = { name: 'X' } as never;
    await tasks.updateTaskTemplate('t1', payload);
    expect(client.put).toHaveBeenCalledWith('/tasks/templates/t1', payload);
  });

  it('deleteTaskTemplate deletes template by key', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tasks.deleteTaskTemplate('t1');
    expect(client.delete).toHaveBeenCalledWith('/tasks/templates/t1');
  });
});

describe('tasks endpoints — tasks CRUD', () => {
  it('listTasks uses default pagination and no filters', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listTasks();
    expect(client.get).toHaveBeenCalledWith('/tasks', {
      params: { offset: 0, limit: 50 },
    });
  });

  it('listTasks merges all provided filters', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listTasks(5, 10, {
      status: 'open',
      category: 'care',
      entity_type: 'plant',
      entity_key: 'p1',
    });
    expect(client.get).toHaveBeenCalledWith('/tasks', {
      params: {
        offset: 5,
        limit: 10,
        status: 'open',
        category: 'care',
        entity_type: 'plant',
        entity_key: 'p1',
      },
    });
  });

  it('createTask posts payload to /tasks', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    const payload = { name: 'water' } as never;
    await tasks.createTask(payload);
    expect(client.post).toHaveBeenCalledWith('/tasks', payload);
  });

  it('getTask gets task by key', async () => {
    client.get.mockResolvedValue({ data: { key: 'tk1' } });
    await tasks.getTask('tk1');
    expect(client.get).toHaveBeenCalledWith('/tasks/tk1');
  });

  it('updateTask puts task by key', async () => {
    client.put.mockResolvedValue({ data: { key: 'tk1' } });
    const payload = { name: 'X' } as never;
    await tasks.updateTask('tk1', payload);
    expect(client.put).toHaveBeenCalledWith('/tasks/tk1', payload);
  });

  it('deleteTask deletes task by key', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tasks.deleteTask('tk1');
    expect(client.delete).toHaveBeenCalledWith('/tasks/tk1');
  });

  it('uploadTaskPhoto posts FormData with multipart header and returns the attachment', async () => {
    // The response is the NFR-013 attachment shape since #1339, not the
    // `{ url, filename, size_bytes }` of the unauthenticated static file this
    // endpoint was originally imagined to write — a file no route ever wrote.
    const attachment = {
      attachment_id: 'att-1',
      uri: '/api/v1/t/mein-garten/attachments/att-1',
      thumbnail_uris: null,
      mime_type: 'image/jpeg',
      byte_size: 1,
      original_filename: 'p.jpg',
    };
    client.post.mockResolvedValue({ data: attachment });
    const file = new File(['x'], 'p.jpg', { type: 'image/jpeg' });
    const result = await tasks.uploadTaskPhoto('tk1', file);
    expect(client.post).toHaveBeenCalledTimes(1);
    const [url, body, opts] = client.post.mock.calls[0];
    expect(url).toBe('/tasks/tk1/photos');
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('file')).toBe(file);
    expect(opts).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } });
    expect(result.attachment_id).toBe('att-1');
  });

  it('taskPhotoUri builds the attachment URI from the id and the active slug', () => {
    // `photo_refs` stores bare ids (NFR-013 §2.2 / AC-09); the URI is rebuilt at
    // render time, which is what survives a tenant rename.
    expect(tasks.taskPhotoUri('att-1')).toMatch(/\/attachments\/att-1$/);
    expect(tasks.taskPhotoUri('att-1', 512)).toMatch(/\/attachments\/att-1\/thumbnails\/512$/);
    expect(tasks.taskPhotoUri('att-1')).toBe('/api/v1/t/mein-garten/attachments/att-1');
  });

  it('startTask posts to start endpoint', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    await tasks.startTask('tk1');
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/start');
  });

  it('completeTask posts completion payload', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    const payload = { completion_notes: 'done' } as never;
    await tasks.completeTask('tk1', payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/complete', payload);
  });

  it('skipTask posts to skip endpoint', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    await tasks.skipTask('tk1');
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/skip');
  });
});

describe('tasks endpoints — specialized queries', () => {
  it('getTaskQueue gets queue without plant filter', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getTaskQueue();
    expect(client.get).toHaveBeenCalledWith('/tasks/queue', { params: {} });
  });

  it('getTaskQueue adds plant_key param when provided', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getTaskQueue('p1');
    expect(client.get).toHaveBeenCalledWith('/tasks/queue', {
      params: { plant_key: 'p1' },
    });
  });

  it('getOverdueTasks gets overdue endpoint', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getOverdueTasks();
    expect(client.get).toHaveBeenCalledWith('/tasks/overdue');
  });

  it('generateCareReminders posts and returns counts', async () => {
    client.post.mockResolvedValue({ data: { created: 2, skipped: 1 } });
    await expect(tasks.generateCareReminders()).resolves.toEqual({ created: 2, skipped: 1 });
    expect(client.post).toHaveBeenCalledWith('/tasks/generate-care-reminders');
  });

  it('getTasksForPlant gets plant tasks without status', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getTasksForPlant('p1');
    expect(client.get).toHaveBeenCalledWith('/tasks/plants/p1', { params: {} });
  });

  it('getTasksForPlant adds status param when provided', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getTasksForPlant('p1', 'open');
    expect(client.get).toHaveBeenCalledWith('/tasks/plants/p1', {
      params: { status: 'open' },
    });
  });
});

describe('tasks endpoints — HST, clone, batch, comments, audit', () => {
  it('validateHST posts validation payload', async () => {
    client.post.mockResolvedValue({ data: { allowed: true } });
    const payload = { task_name: 'topping', current_phase: 'flower' };
    await tasks.validateHST(payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/validate-hst', payload);
  });

  it('cloneTask posts default empty payload', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk2' } });
    await tasks.cloneTask('tk1');
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/clone', {});
  });

  it('reopenTask posts empty body', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    await tasks.reopenTask('tk1');
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/reopen', {});
  });

  it('batchStatusChange posts keys, action and notes', async () => {
    client.post.mockResolvedValue({ data: { succeeded: 1 } });
    await tasks.batchStatusChange(['a', 'b'], 'complete', 'all done');
    expect(client.post).toHaveBeenCalledWith('/tasks/batch/status', {
      task_keys: ['a', 'b'],
      action: 'complete',
      completion_notes: 'all done',
    });
  });

  it('batchDelete posts task keys', async () => {
    client.post.mockResolvedValue({ data: { succeeded: 2 } });
    await tasks.batchDelete(['a', 'b']);
    expect(client.post).toHaveBeenCalledWith('/tasks/batch/delete', {
      task_keys: ['a', 'b'],
    });
  });

  it('batchAssign posts keys and assignee', async () => {
    client.post.mockResolvedValue({ data: { succeeded: 1 } });
    await tasks.batchAssign(['a'], 'u1');
    expect(client.post).toHaveBeenCalledWith('/tasks/batch/assign', {
      task_keys: ['a'],
      assigned_to_user_key: 'u1',
    });
  });

  it('listTaskComments gets comments for task', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.listTaskComments('tk1');
    expect(client.get).toHaveBeenCalledWith('/tasks/tk1/comments');
  });

  it('createTaskComment posts comment text', async () => {
    client.post.mockResolvedValue({ data: { key: 'c1' } });
    await tasks.createTaskComment('tk1', 'hi');
    expect(client.post).toHaveBeenCalledWith('/tasks/tk1/comments', {
      comment_text: 'hi',
    });
  });

  it('updateTaskComment puts updated text', async () => {
    client.put.mockResolvedValue({ data: { key: 'c1' } });
    await tasks.updateTaskComment('tk1', 'c1', 'edited');
    expect(client.put).toHaveBeenCalledWith('/tasks/tk1/comments/c1', {
      comment_text: 'edited',
    });
  });

  it('deleteTaskComment deletes comment', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tasks.deleteTaskComment('tk1', 'c1');
    expect(client.delete).toHaveBeenCalledWith('/tasks/tk1/comments/c1');
  });

  it('getTaskHistory gets audit history', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tasks.getTaskHistory('tk1');
    expect(client.get).toHaveBeenCalledWith('/tasks/tk1/history');
  });

  it('getWorkflowExecution gets execution by key', async () => {
    client.get.mockResolvedValue({ data: { key: 'e1' } });
    await tasks.getWorkflowExecution('e1');
    expect(client.get).toHaveBeenCalledWith('/tasks/executions/e1');
  });

  it('addTaskToWorkflow posts task to execution', async () => {
    client.post.mockResolvedValue({ data: { key: 'tk1' } });
    const payload = { name: 'extra' } as never;
    await tasks.addTaskToWorkflow('e1', payload);
    expect(client.post).toHaveBeenCalledWith('/tasks/executions/e1/tasks', payload);
  });
});
