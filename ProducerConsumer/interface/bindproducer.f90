module bindproducer
use iso_c_binding
use bind_data

implicit none

interface

    type(c_ptr) function bind_create_producer_impl(broker, product) bind(c, name='create_producer')
        use iso_c_binding
        character(kind=c_char), intent(in) :: broker(*)
        character(kind=c_char), intent(in) :: product(*)
    end function

    subroutine aws_put_metric_impl(namespace, metricname, value, normalizeunixtime) bind(c, name='aws_put_metric')
        use iso_c_binding
        character(kind=c_char), intent(in) :: namespace(*)
        character(kind=c_char), intent(in) :: metricname(*)
        integer(c_long_long), intent(in), VALUE :: value
        logical(c_bool), intent(in), VALUE :: normalizeunixtime
    end subroutine

    subroutine bind_produce_impl(producer, key, data, datasize, topic) bind(c, name='produce')
        use iso_c_binding
        import fKeyMessage
        type(c_ptr), value, intent(in) :: producer
        type(fKeyMessage), intent(in) :: key
        type(c_ptr), value, intent(in) :: data
        integer(c_size_t), intent(in), VALUE :: datasize
        character(kind=c_char), intent(in) :: topic(*)
    end subroutine

end interface

contains 

pure function f_c_string_func (f_string) result (c_string)
  use, intrinsic :: iso_c_binding, only: c_char, c_null_char
  implicit none
  character(len=*), intent(in) :: f_string
  character(len=1, kind=c_char) :: c_string(len_trim(f_string)+1)
  integer :: n,i

  n = len_trim(f_string)
  do i =1, n
    c_string(i) = f_string(i:i)
  end do
  c_string(n+1) = c_null_char
end function f_c_string_func

function bind_create_producer(broker, product) result(producer)
    use iso_c_binding
    character(kind=c_char, len=*), intent(in) :: broker
    character(kind=c_char, len=*), intent(in) :: product
    type(c_ptr) :: producer

    producer = bind_create_producer_impl(f_c_string_func(broker), f_c_string_func(product))
end function

subroutine aws_put_metric(namespace, metricname, value, normalizeunixtime) 
    use iso_c_binding
    character(kind=c_char, len=*), intent(in) :: namespace
    character(kind=c_char, len=*), intent(in) :: metricname
    integer(c_long_long), intent(in) :: value
    logical(c_bool), intent(in), VALUE :: normalizeunixtime
    call aws_put_metric_impl(f_c_string_func(namespace), f_c_string_func(metricname), value, normalizeunixtime)
end subroutine

subroutine bind_produce_3d(producer, field, fieldname, npatches, myrank, datetime, &
    ilonstart, jlatstart, totlonlen, totlatlen,                  &
    longitudeOfFirstGridPoint, longitudeOfLastGridPoint, latitudeOfFirstGridPoint, latitudeOfLastGridPoint)
    use iso_c_binding
    type(c_ptr), value, intent(in) :: producer
    real(c_float), pointer :: field(:,:,:)
    character(kind=c_char, len=*), intent(in) :: fieldname
    integer(c_int), intent(in) :: npatches
    integer(c_int), intent(in) :: myrank
    integer(c_size_t), intent(in) :: datetime
    integer(c_size_t), intent(in) :: ilonstart, jlatstart, totlonlen, totlatlen
    real(c_float), intent(in) :: longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
            latitudeOfFirstGridPoint, latitudeOfLastGridPoint

    type(fKeyMessage) :: keyMsg
    integer:: k
    integer :: levlen = 1
    integer(kind=c_size_t) :: datasize

    datasize =  size(field,1)*size(field,2)*4

    levlen = size(field,3)

    keyMsg%actionType = 1
    keyMsg%key=f_c_string_func(fieldname)
    keyMsg%npatches = npatches
    keyMsg%myrank=myrank
    keyMsg%datetime=datetime
    keyMsg%ilon_start=ilonstart
    keyMsg%jlat_start=jlatstart
    keyMsg%lev=0
    keyMsg%lonlen=size(field,1)
    keyMsg%latlen=size(field,2)
    keyMsg%levlen=levlen
    keyMsg%totlonlen=totlonlen
    keyMsg%totlatlen=totlatlen
    keyMsg%longitudeOfFirstGridPoint=longitudeOfFirstGridPoint
    keyMsg%longitudeOfLastGridPoint=longitudeOfLastGridPoint
    keyMsg%latitudeOfFirstGridPoint=latitudeOfFirstGridPoint
    keyMsg%latitudeOfLastGridPoint=latitudeOfLastGridPoint
  
    do k=1, size(field,3)
        keyMsg%lev = k-1
        call bind_produce_impl(producer, keyMsg, c_loc(field(:,:,k)), datasize, f_c_string_func(fieldname))
    enddo 

    end subroutine

    subroutine bind_produce_2d(producer, field, fieldname, npatches, myrank, datetime, &
        ilonstart, jlatstart, totlonlen, totlatlen,                  &
        longitudeOfFirstGridPoint, longitudeOfLastGridPoint, latitudeOfFirstGridPoint, latitudeOfLastGridPoint)
        use iso_c_binding
        type(c_ptr), value, intent(in) :: producer
        real(c_float), pointer :: field(:,:)
        character(kind=c_char, len=*), intent(in) :: fieldname
        integer(c_int), intent(in) :: npatches
        integer(c_int), intent(in) :: myrank
        integer(c_size_t), intent(in) :: datetime
        integer(c_size_t), intent(in) :: ilonstart, jlatstart, totlonlen, totlatlen
        real(c_float), intent(in) :: longitudeOfFirstGridPoint, longitudeOfLastGridPoint, &
                latitudeOfFirstGridPoint, latitudeOfLastGridPoint
    
        type(fKeyMessage) :: keyMsg
        integer :: levlen = 1
        integer(kind=c_size_t) :: datasize

        datasize =  size(field,1)*size(field,2)*4
    

        keyMsg%actionType = 1
        keyMsg%key=f_c_string_func(fieldname)
        keyMsg%npatches = npatches
        keyMsg%myrank=myrank
        keyMsg%datetime=datetime
        keyMsg%ilon_start=ilonstart
        keyMsg%jlat_start=jlatstart
        keyMsg%lev=0
        keyMsg%lonlen=size(field,1)
        keyMsg%latlen=size(field,2)
        keyMsg%levlen=levlen
        keyMsg%totlonlen=totlonlen
        keyMsg%totlatlen=totlatlen
        keyMsg%longitudeOfFirstGridPoint=longitudeOfFirstGridPoint
        keyMsg%longitudeOfLastGridPoint=longitudeOfLastGridPoint
        keyMsg%latitudeOfFirstGridPoint=latitudeOfFirstGridPoint
        keyMsg%latitudeOfLastGridPoint=latitudeOfLastGridPoint
      
        call bind_produce_impl(producer, keyMsg, c_loc(field(:,:)), datasize, f_c_string_func(fieldname))
    
    end subroutine
    
end
