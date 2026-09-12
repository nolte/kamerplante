import ErrorPage from './ErrorPage';

export default function NotFoundPage() {
  return <ErrorPage statusCode={404} landmark={false} />;
}
