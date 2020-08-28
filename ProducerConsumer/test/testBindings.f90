program testBindings

  use bind_data
  use bindproducer
  use iso_c_binding

  implicit none

#ifdef ENABLE_MPI
include 'mpif.h'
#endif

  type(c_ptr) :: producer
  integer, parameter :: sp = SELECTED_REAL_KIND( 6, 37) !< single precision

  real (kind=sp), POINTER :: field_3d(:,:,:)
  real (kind=sp), POINTER :: field_2d(:,:)

  integer :: izl
  integer :: dxsize = 32
  integer :: dysize = 32

  integer(kind=c_int) :: npatches = 1
  integer(kind=c_size_t) :: datetime = 0
  integer(kind=c_size_t) :: ilonstart, jlatstart, totlonlen, totlatlen
  character(kind=c_char, len = 32) :: fieldname
  real (kind=c_float) :: longitudeOfFirstGridPoint = 0
  real(kind=c_float) :: longitudeOfLastGridPoint = 0
  real(kind=c_float) :: latitudeOfFirstGridPoint = 0
  real(kind=c_float) :: latitudeOfLastGridPoint = 0

  integer :: i,j,k, levlen
  
  integer :: ierror, mpisize, mpirank, nx, ny, px, py
  CHARACTER(len=255) :: kafkabroker

  
#ifdef ENABLE_MPI
  call mpi_init(ierror)
  call mpi_comm_size(MPI_COMM_WORLD, mpisize, ierror)
  call mpi_comm_rank(MPI_COMM_WORLD, mpirank, ierror)
  nx = 2
  ny = mpisize / nx
  if( mod(mpisize, 2) .ne. 0) then
    call mpi_abort(MPI_COMM_WORLD, ierror)
  end if

  px = mod(mpirank , 2)
  py = mpirank / 2
#else
  mpirank = 0
  mpisize=1
  nx = 1
  ny = 1
  px = 0
  py = 0
#endif

  ilonstart = dxsize * px
  jlatstart = dysize * py
  totlonlen = dxsize * nx
  totlatlen = dysize * ny

  levlen=10
  allocate ( field_3d   (dxsize,dysize,levlen)  , stat=izl )
  allocate ( field_2d   (dxsize,dysize)  , stat=izl )

  do i=1, dxsize
    do j=1, dysize
      do k=1, levlen
        field_3d(i,j,k) = k*10 + mpirank
        field_2d(i,j) = mpirank
      enddo
    enddo
  enddo
  CALL get_environment_variable("KAFKABROKER", kafkabroker)

  producer = bind_create_producer(TRIM(kafkabroker), "ftest")

#ifdef ENABLE_MPI
  npatches = mpisize
#endif

  fieldname = "TestFIELD_3d"
  call bind_produce_3d(producer, field_3d, fieldname, npatches, mpirank, datetime, &
      ilonstart, jlatstart, totlonlen, totlatlen, &
      longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint)
 
  fieldname = "TestFIELD_2d"

  call bind_produce_2d(producer, field_2d, fieldname, npatches, mpirank, datetime, &
      ilonstart, jlatstart, totlonlen, totlatlen, &
      longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint)

#ifdef ENABLE_MPI
  call mpi_finalize()
#endif
    

end program
