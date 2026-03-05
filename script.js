const form = document.querySelector('#person-form');
const result = document.querySelector('#result');

form.addEventListener('submit', (event) => {
  event.preventDefault();

  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const data = Object.fromEntries(new FormData(form).entries());

  result.innerHTML = `
    <h2>Данные сохранены</h2>
    <p><strong>Имя:</strong> ${data.firstName}</p>
    <p><strong>Фамилия:</strong> ${data.lastName}</p>
    <p><strong>Возраст:</strong> ${data.age}</p>
    <p><strong>Email:</strong> ${data.email}</p>
    <p><strong>Город:</strong> ${data.city || '—'}</p>
    <p><strong>О себе:</strong> ${data.about || '—'}</p>
  `;
  result.classList.add('visible');
});
