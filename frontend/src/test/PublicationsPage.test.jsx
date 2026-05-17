import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PublicationsPage from '../pages/PublicationsPage';
import client from '../api/client';

vi.mock('../api/client');

const mockPubs = [
  {
    publicationId: 77,
    channelId: 1,
    channelCode: 'TELEGRAM',
    channelName: 'Telegram',
    destinationId: 5,
    destinationLabel: 'Основной канал',
    status: 'PUBLISHED',
    externalId: 'tg-abc',
    externalUrl: 'https://t.me/c/123/456',
    createdAt: '2026-04-15T10:00:00Z',
  },
  {
    publicationId: 78,
    channelId: 1,
    channelCode: 'TELEGRAM',
    channelName: 'Telegram',
    destinationId: 5,
    destinationLabel: 'Основной канал',
    status: 'RECALLED',
    externalId: 'tg-xyz',
    createdAt: '2026-04-15T11:00:00Z',
  },
];

const mockReports = [
  {
    id: 41,
    companyId: 10,
    companyName: 'Тестовая компания',
    status: 'PENDING',
    createdAt: '2026-04-15T09:00:00Z',
  },
  {
    id: 42,
    companyId: 10,
    companyName: 'Тестовая компания',
    status: 'CONFIRMED',
    createdAt: '2026-04-15T12:00:00Z',
  },
];

const mockDestinations = [
  { id: 5, label: 'Основной канал', channelName: 'Telegram', channelCode: 'TELEGRAM' },
];

function mockPageData({ publications = mockPubs, reports = mockReports, destinations = mockDestinations } = {}) {
  client.get = vi.fn().mockImplementation((url) => {
    if (url === '/companies/10') {
      return Promise.resolve({ data: { id: 10, name: 'Тестовая компания' } });
    }
    if (url === '/publish/destinations') {
      return Promise.resolve({ data: destinations });
    }
    if (url === '/reports/top-n') {
      return Promise.resolve({ data: reports });
    }
    if (url === '/publications') {
      return Promise.resolve({ data: publications });
    }
    return Promise.resolve({ data: [] });
  });
}

describe('PublicationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('lastUserId', '1');
    localStorage.setItem('companySnapshots', JSON.stringify([{ id: 10, name: 'Тестовая компания', userId: 1 }]));
  });

  it('рендерит основные секции страницы', () => {
    render(<PublicationsPage />);
    expect(screen.getByText('Сформированные рейтинги')).toBeInTheDocument();
    expect(screen.getByText('Опубликовать рейтинг')).toBeInTheDocument();
    expect(screen.getByText('История публикаций')).toBeInTheDocument();
  });

  it('после выбора компании автоматически загружает историю публикаций', async () => {
    mockPageData();

    render(<PublicationsPage />);
    fireEvent.change(screen.getByLabelText('Компания'), { target: { value: '10' } });

    await waitFor(() => expect(screen.getByText('tg-abc')).toBeInTheDocument());
    expect(screen.getByText('Опубликован')).toBeInTheDocument();
    expect(screen.getByText('Отозван')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Пост' })).toHaveAttribute('href', 'https://t.me/c/123/456');
  });

  it('в форме публикации показывает только confirmed-рейтинги', async () => {
    mockPageData();

    render(<PublicationsPage />);
    fireEvent.change(screen.getByLabelText('Компания'), { target: { value: '10' } });

    const reportSelect = await screen.findByLabelText('Выберите рейтинг');
    await waitFor(() => expect(reportSelect.querySelectorAll('option')).toHaveLength(2));

    const optionValues = Array.from(reportSelect.options).map(option => option.value);
    expect(optionValues).toEqual(['', '42']);
  });

  it('кнопка отмены есть только у PUBLISHED Telegram-публикаций', async () => {
    mockPageData();

    render(<PublicationsPage />);
    fireEvent.change(screen.getByLabelText('Компания'), { target: { value: '10' } });

    await waitFor(() => expect(screen.getByText('tg-abc')).toBeInTheDocument());
    expect(screen.getAllByRole('button', { name: /отмена/i })).toHaveLength(1);
  });

  it('после отмены публикации статус строки обновляется на RECALLED', async () => {
    mockPageData();
    client.post = vi.fn().mockResolvedValue({
      data: {
        publicationId: 77,
        channelId: 1,
        channelCode: 'TELEGRAM',
        channelName: 'Telegram',
        destinationId: 5,
        destinationLabel: 'Основной канал',
        status: 'RECALLED',
        externalId: 'tg-abc',
        externalUrl: 'https://t.me/c/123/456',
        createdAt: '2026-04-15T10:00:00Z',
      },
    });

    render(<PublicationsPage />);
    fireEvent.change(screen.getByLabelText('Компания'), { target: { value: '10' } });

    await waitFor(() => expect(screen.getByRole('button', { name: /отмена/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /отмена/i }));

    await waitFor(() => expect(screen.getAllByText('Отозван')).toHaveLength(2));
    expect(screen.queryByRole('button', { name: /отмена/i })).not.toBeInTheDocument();
  });

  it('показывает подсказку, если подтверждённых рейтингов нет', async () => {
    mockPageData({
      reports: [
        {
          id: 41,
          companyId: 10,
          companyName: 'Тестовая компания',
          status: 'PENDING',
          createdAt: '2026-04-15T09:00:00Z',
        },
      ],
      publications: [],
    });

    render(<PublicationsPage />);
    fireEvent.change(screen.getByLabelText('Компания'), { target: { value: '10' } });

    await waitFor(() =>
      expect(screen.getByText(/Нет подтверждённых рейтингов/i)).toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: 'Опубликовать' })).toBeDisabled();
  });
});
